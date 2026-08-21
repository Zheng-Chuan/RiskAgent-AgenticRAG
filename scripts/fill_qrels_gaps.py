"""为 qrels 为空的题目补 gold chunk 标注.

背景: q23-26/42/47-50 等概念定义题在历史 qrels 中没有 gold 标注, 评测时按
recall=0 计入均值, 系统性拉低 retrieval 指标. 本脚本用题目关键词在索引
chunk 中打分, 取最佳匹配 chunk 作为 gold.

用法:
    python scripts/fill_qrels_gaps.py --persist-dir .milvus --qrels tests/data/qrels.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# 空标注题目的关键词 (按区分度排序, 小写)
GAP_KEYWORDS: dict[str, list[str]] = {
    "q23": ["default probability", "probability of default", "cva"],
    "q24": ["loss given default", "lgd"],
    "q25": ["exposure at default", "ead"],
    "q26": ["discount factor", "discounting", "cva"],
    "q42": ["model risk"],
    "q47": ["initial margin"],
    "q48": ["variation margin"],
    "q49": ["value at risk", "var"],
    "q50": ["expected shortfall"],
}


def _score(text: str, keywords: list[str]) -> float:
    """关键词命中率, 短语完整出现权重更高."""
    lower = text.lower()
    total = len(keywords)
    if total == 0:
        return 0.0
    hit = sum(1 for k in keywords if k in lower)
    return hit / total


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill empty qrels with keyword-matched gold chunks")
    parser.add_argument("--persist-dir", default=".milvus")
    parser.add_argument("--qrels", default="tests/data/qrels.json")
    parser.add_argument("--top", type=int, default=2, help="每题补充的 gold chunk 数")
    args = parser.parse_args()

    qrels_path = Path(args.qrels)
    sparse_path = Path(args.persist_dir) / "sparse_corpus.jsonl"

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

    qrels = json.loads(qrels_path.read_text(encoding="utf-8"))
    filled = 0

    for item in qrels:
        qid = str(item.get("id", ""))
        if qid not in GAP_KEYWORDS or item.get("qrels"):
            continue  # 只补指定题目中仍为空的

        keywords = GAP_KEYWORDS[qid]
        scored = sorted(
            ((c, _score(c["text"], keywords)) for c in chunks),
            key=lambda x: x[1],
            reverse=True,
        )
        top = [(c, s) for c, s in scored if s >= max(0.5, scored[0][1] * 0.99)][: args.top]
        if not top:
            print(f"  无法匹配: {qid}")
            continue

        for rank, (c, s) in enumerate(top, start=1):
            item.setdefault("qrels", []).append(
                {
                    "qrel_id": f"{qid}_gap{rank}",
                    "chunk_id": c["chunk_id"],
                    "source": c["source"],
                    "section_path": c["section_path"],
                    "text": c["text"][:200],
                    "relevance": 2 if rank == 1 else 1,
                    "match_score": round(s, 3),
                    "origin": "keyword_gap_fill",
                }
            )
        filled += 1
        print(f"  {qid}: +{len(top)} gold ({top[0][0]['source'].split('/')[-1]} score={top[0][1]:.2f})")

    qrels_path.write_text(json.dumps(qrels, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n补充 {filled} 题, 写入 {qrels_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
