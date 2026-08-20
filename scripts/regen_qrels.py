"""重新生成 qrels, 把旧 gold 文本映射到重建索引后的新 chunk_id.

背景: chunking 修复后 chunk_id 全部变化, 旧 qrels 引用的 chunk_id 在新索引中不存在.
本脚本用 gold 文本匹配 (精确 -> 句级包含打分) 找到新 chunk_id, 并补充同 section 的
chunk 作为多 gold 标注, 提升评测的召回判定公平性.

用法:
    python scripts/regen_qrels.py --persist-dir .milvus_fix --qrels tests/data/qrels.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _sentences(text: str) -> list[str]:
    """把 gold 文本切成句子 (用于模糊包含打分)."""
    parts = re.split(r"(?<=[.!?。])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 12]


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "will", "have", "has", "had", "not", "but", "its", "their", "than", "when",
    "what", "which", "who", "whom", "how", "why", "where", "into", "over",
    "under", "such", "also", "than", "then", "them", "they", "there", "these",
    "those", "been", "being", "each", "other", "some", "any", "all", "more",
    "most", "less", "least", "very", "much", "many", "given", "including",
}


def _keywords(text: str) -> list[str]:
    """提取 gold 文本的区分性关键词 (小写, >=4 字符, 去停用词)."""
    words = re.findall(r"[a-z]{4,}", text.lower())
    return [w for w in dict.fromkeys(words) if w not in _STOPWORDS]


def _keyword_score(gold_text: str, chunk_text: str) -> float:
    """关键词覆盖率兜底: gold 关键词出现在 chunk 中的比例."""
    kws = _keywords(gold_text)
    if not kws:
        return 0.0
    lower = chunk_text.lower()
    hit = sum(1 for k in kws if k in lower)
    return hit / len(kws)


def _match_score(gold_text: str, chunk_text: str) -> float:
    """gold 文本与 chunk 的包含匹配得分: 覆盖的 gold 字符比例."""
    if not gold_text or not chunk_text:
        return 0.0
    score = 0.0
    for sent in _sentences(gold_text):
        # 句子太长时取前 80 字符做包含探测
        probe = sent if len(sent) <= 80 else sent[:80]
        if probe in chunk_text:
            score += len(sent)
    return score / max(1, len(gold_text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate qrels against a rebuilt index")
    parser.add_argument("--persist-dir", default=".milvus_fix", help="重建索引的持久化目录")
    parser.add_argument("--qrels", default="tests/data/qrels.json", help="旧 qrels 文件路径")
    parser.add_argument("--backup", action="store_true", default=True, help="备份旧 qrels 为 .bak")
    args = parser.parse_args()

    qrels_path = Path(args.qrels)
    sparse_path = Path(args.persist_dir) / "sparse_corpus.jsonl"

    # 先保存原始文件内容 (qrels 对象后续会被就地修改, 不能用修改后的对象做备份)
    original_text = qrels_path.read_text(encoding="utf-8")
    qrels = json.loads(original_text)

    # 读取新索引的全部 chunk
    chunks: list[dict] = []
    for ln in sparse_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        meta = row.get("metadata") or {}
        chunks.append(
            {
                "chunk_id": str(meta.get("chunk_id", "")),
                "source": str(meta.get("source", "")),
                "section_path": str(meta.get("section_path", "")),
                "text": str(row.get("page_content", "")),
            }
        )
    print(f"新索引 chunk 总数: {len(chunks)}")

    matched = 0
    unmatched = 0
    source_missing = 0
    multi_gold_added = 0

    # 新索引覆盖的源文件名集合 (用于判断 gold 引用的文件是否被索引)
    indexed_files = {c["source"].split("/")[-1] for c in chunks}

    for item in qrels:
        new_qrels: list[dict] = []
        seen_chunk_ids: set[str] = set()
        for r in item.get("qrels", []):
            gold_text = str(r.get("text", ""))
            old_id = str(r.get("chunk_id", ""))

            # gold 引用的源文件不在新索引中 (如未索引的 PDF), 丢弃该 qrel
            src_file = old_id.split(":")[0]
            if src_file not in indexed_files:
                source_missing += 1
                print(f"  源未索引: {item['id']} {old_id}")
                continue

            # 1) 精确文本匹配
            best_id, best_score = "", 0.0
            for c in chunks:
                if gold_text and gold_text.strip() == c["text"].strip():
                    best_id, best_score = c["chunk_id"], 1.0
                    break

            # 2) 同 source 内句级包含 + 关键词覆盖打分
            if not best_id:
                pool = [c for c in chunks if c["source"].split("/")[-1] == src_file]
                for c in pool:
                    s = max(_match_score(gold_text, c["text"]), _keyword_score(gold_text, c["text"]))
                    if s > best_score:
                        best_id, best_score = c["chunk_id"], s

            if best_id and best_score >= 0.4:
                entry = dict(r)
                entry["chunk_id"] = best_id
                entry["old_chunk_id"] = old_id
                entry["match_score"] = round(best_score, 3)
                new_qrels.append(entry)
                # 同一 gold chunk 允许被多个 qrel 引用 (不同小问指向同一答案文本),
                # seen_chunk_ids 仅用于 multi-gold 补充标注的去重
                if best_id not in seen_chunk_ids:
                    seen_chunk_ids.add(best_id)
                matched += 1

                # 多 gold: 同 source 同 section 的其他 chunk 作为补充标注 (relevance 降为 1)
                best_section = next((c["section_path"] for c in chunks if c["chunk_id"] == best_id), "")
                extras = [
                    c
                    for c in chunks
                    if c["chunk_id"] != best_id
                    and c["chunk_id"] not in seen_chunk_ids
                    and c["source"].split("/")[-1] == src_file
                    and best_section
                    and c["section_path"] == best_section
                ][:2]
                for c in extras:
                    new_qrels.append(
                        {
                            "qrel_id": f"{item['id']}_x{len(new_qrels)}",
                            "chunk_id": c["chunk_id"],
                            "source": c["source"],
                            "section_path": c["section_path"],
                            "text": c["text"][:200],
                            "relevance": 1,
                        }
                    )
                    seen_chunk_ids.add(c["chunk_id"])
                    multi_gold_added += 1
            else:
                unmatched += 1
                print(f"  未匹配: {item['id']} {old_id} score={best_score:.2f} text={gold_text[:60]!r}")

        item["qrels"] = new_qrels

    print(f"\n匹配结果: {matched} matched, {unmatched} unmatched, {source_missing} source_not_indexed, {multi_gold_added} multi-gold added")

    if args.backup:
        bak = qrels_path.with_suffix(".json.bak")
        bak.write_text(original_text, encoding="utf-8")
        print(f"旧 qrels 已备份到 {bak}")

    qrels_path.write_text(json.dumps(qrels, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新 qrels 已写入 {qrels_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
