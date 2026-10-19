"""Backfill empty context_brief fields in sparse_corpus.jsonl (RFC-006 C2 llm_brief 前置).

索引重建期 _generate_context_briefs 逐 chunk 调 LLM, 撞治理限流即静默置空
(实测 d457/xva 等大文档 brief 全空). llm_brief 变体只消费 sparse_corpus.jsonl
metadata 里的 context_brief (bm25_effective_text), 因此补齐该文件即可, 不动
Milvus dense rows (embedding 侧本就不注入).

对每个空 brief chunk 用与 indexer 相同的 prompt (parent 文本前 8000 字符 +
chunk 正文) 生成 brief, 遇 LLMGovernanceError 按 retry_after_s 退避重试.
已生成过的 chunk 原样保留, 脚本可重复运行.

用法:
  python -m scripts.backfill_context_briefs --persist-dir .milvus [--limit N]
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from riskagent_agenticrag.llm.generate import call_llm_text
from riskagent_agenticrag.llm.governance import LLMGovernanceError


def _load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    with path.open() as f:
        for raw in f:
            line = raw.strip()
            if line:
                out.append(json.loads(line))
    return out


def _dump_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _call_with_governance_retry(prompt: str, *, max_attempts: int = 30) -> str:
    for attempt in range(max_attempts):
        try:
            resp = call_llm_text(prompt, temperature=0.0, estimated_tokens=2500)
            return str(resp).strip()[:200]
        except LLMGovernanceError as exc:
            if attempt >= max_attempts - 1:
                raise
            wait = exc.metadata.get("retry_after_s") or 5.0
            time.sleep(min(float(wait), 60.0))
        except Exception:
            raise
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persist-dir", type=Path, default=Path(".milvus"))
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个空 brief (0 = 全部)")
    parser.add_argument("--workers", type=int, default=8, help="并发 LLM 调用数")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写回")
    args = parser.parse_args()

    sparse_path = args.persist_dir / "sparse_corpus.jsonl"
    parent_path = args.persist_dir / "parent_corpus.jsonl"

    chunks = _load_jsonl(sparse_path)
    parents_by_id: dict[str, dict] = {}
    for p in _load_jsonl(parent_path):
        pid = str((p.get("metadata") or {}).get("parent_id") or "")
        if pid:
            parents_by_id[pid] = p

    empty = [
        i
        for i, c in enumerate(chunks)
        if not str((c.get("metadata") or {}).get("context_brief") or "").strip()
    ]
    total = len(chunks)
    print(f"chunks={total} empty_briefs={len(empty)}")
    if args.limit > 0:
        empty = empty[: args.limit]

    def _fill_one(idx: int) -> bool:
        chunk = chunks[idx]
        meta = chunk.get("metadata") or {}
        pid = str(meta.get("parent_id") or "")
        parent = parents_by_id.get(pid)
        whole_doc = (parent or {}).get("page_content") or ""
        chunk_text = chunk.get("page_content") or ""
        if not whole_doc or not chunk_text:
            return False
        prompt = (
            f"<document>\n{whole_doc[:8000]}\n</document>\n"
            f"Here is the chunk we want to situate within the whole document:\n"
            f"<chunk>\n{chunk_text}\n</chunk>\n"
            f"Please give a short succinct context to situate this chunk within the overall document "
            f"for the purposes of improving search retrieval of the chunk. "
            f"Answer only with the succinct context and nothing else."
        )
        try:
            brief = _call_with_governance_retry(prompt)
        except Exception as exc:
            print(f"FAILED chunk={meta.get('chunk_id')}: {exc}")
            return False
        if not brief:
            return False
        meta["context_brief"] = brief
        chunk["metadata"] = meta
        return True

    filled = 0
    failed = 0
    workers = max(1, args.workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fill_one, idx): idx for idx in empty}
        for n, fut in enumerate(as_completed(futures), 1):
            if fut.result():
                filled += 1
            else:
                failed += 1
            if n % 25 == 0 or n == len(empty):
                print(f"[{n}/{len(empty)}] filled={filled} failed={failed}")

    if not args.dry_run and filled:
        _dump_jsonl(sparse_path, chunks)
        print(f"wrote {sparse_path} (filled={filled} failed={failed})")
    else:
        print(f"dry-run/no-fill: filled={filled} failed={failed}")


if __name__ == "__main__":
    main()
