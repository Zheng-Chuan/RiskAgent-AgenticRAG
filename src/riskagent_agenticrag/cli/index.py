from __future__ import annotations

import argparse
from pathlib import Path

from riskagent_agenticrag.indexing.indexer import incremental_index


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="riskagent_agenticrag.index")
    p.add_argument("--corpus-dir", default="corpus")
    p.add_argument("--persist-dir", default=".milvus")
    p.add_argument(
        "--path",
        action="append",
        default=[],
        help="Index only the specified file path (repeatable). Defaults to indexing all corpus files.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    corpus_dir = Path(args.corpus_dir)
    persist_dir = Path(args.persist_dir)
    include = [Path(p) for p in (args.path or []) if str(p or "").strip()]
    result = incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=include or None)
    print("Index updated")
    print(f"- persist_dir: {result.persist_dir}")
    print(f"- indexed_sources: {len(result.indexed_sources)}")
    print(f"- skipped_sources: {len(result.skipped_sources)}")
    print(f"- chunk_indexed: {result.chunk_indexed}")


if __name__ == "__main__":
    main()

