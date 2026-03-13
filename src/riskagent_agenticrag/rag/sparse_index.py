"""稀疏索引 -- BM25 语料的 JSONL 持久化."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.rag.utils import load_docs_jsonl, persist_docs_jsonl

SPARSE_CORPUS_FILENAME = "sparse_corpus.jsonl"


def persist_sparse_corpus(*, chunks: list[Document], persist_dir: Path) -> str:
    return persist_docs_jsonl(chunks, persist_dir / SPARSE_CORPUS_FILENAME)


def load_sparse_corpus(*, persist_dir: Path) -> list[Document]:
    return load_docs_jsonl(persist_dir / SPARSE_CORPUS_FILENAME)


def sparse_corpus_stats(*, persist_dir: Path) -> dict[str, Any]:
    docs = load_sparse_corpus(persist_dir=persist_dir)
    return {"count": len(docs), "path": str(persist_dir / SPARSE_CORPUS_FILENAME)}
