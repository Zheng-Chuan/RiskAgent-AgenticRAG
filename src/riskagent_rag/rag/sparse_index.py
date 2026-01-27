from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]


SPARSE_CORPUS_FILENAME = "sparse_corpus.jsonl"


def persist_sparse_corpus(*, chunks: list[Document], persist_dir: Path) -> str:
    persist_dir.mkdir(parents=True, exist_ok=True)
    path = persist_dir / SPARSE_CORPUS_FILENAME
    with path.open("w", encoding="utf-8") as f:
        for d in chunks:
            meta = d.metadata or {}
            row = {"page_content": d.page_content or "", "metadata": meta}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(path)


def load_sparse_corpus(*, persist_dir: Path) -> list[Document]:
    path = persist_dir / SPARSE_CORPUS_FILENAME
    if not path.exists():
        return []
    docs: list[Document] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        page_content = str(data.get("page_content", "") or "")
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs


def sparse_corpus_stats(*, persist_dir: Path) -> dict[str, Any]:
    docs = load_sparse_corpus(persist_dir=persist_dir)
    return {"count": len(docs), "path": str((persist_dir / SPARSE_CORPUS_FILENAME))}
