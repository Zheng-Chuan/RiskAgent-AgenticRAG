"""稀疏索引模块测试.

覆盖 rag/sparse_index.py: persist / load / stats.
"""

from __future__ import annotations

import pathlib

import pytest
from langchain_core.documents import Document
from riskagent_agenticrag.rag.sparse_index import (
    SPARSE_CORPUS_FILENAME,
    load_sparse_corpus,
    persist_sparse_corpus,
    sparse_corpus_stats,
)


@pytest.mark.unit
class TestSparseIndex:
    """稀疏语料持久化测试."""

    def test_persist_and_load_roundtrip(self, tmp_path: pathlib.Path):
        """写入后读回应保持一致."""
        chunks = [
            Document(page_content="delta risk", metadata={"chunk_id": "c1", "source": "doc.md"}),
            Document(page_content="vega risk", metadata={"chunk_id": "c2", "source": "doc2.md"}),
        ]
        path = persist_sparse_corpus(chunks=chunks, persist_dir=tmp_path)
        assert pathlib.Path(path).exists()
        assert SPARSE_CORPUS_FILENAME in path

        loaded = load_sparse_corpus(persist_dir=tmp_path)
        assert len(loaded) == 2
        assert loaded[0].page_content == "delta risk"

    def test_load_missing_returns_empty(self, tmp_path: pathlib.Path):
        """文件不存在时返回空列表."""
        assert load_sparse_corpus(persist_dir=tmp_path) == []

    def test_stats_returns_count_and_path(self, tmp_path: pathlib.Path):
        """统计应返回 count 和 path."""
        chunks = [Document(page_content="x", metadata={})]
        persist_sparse_corpus(chunks=chunks, persist_dir=tmp_path)
        stats = sparse_corpus_stats(persist_dir=tmp_path)
        assert stats["count"] == 1
        assert SPARSE_CORPUS_FILENAME in stats["path"]

    def test_stats_empty_when_no_file(self, tmp_path: pathlib.Path):
        """无文件时统计 count 为 0."""
        stats = sparse_corpus_stats(persist_dir=tmp_path)
        assert stats["count"] == 0

    def test_persist_empty_chunks(self, tmp_path: pathlib.Path):
        """空 chunks 列表也应写入文件 (空文件)."""
        persist_sparse_corpus(chunks=[], persist_dir=tmp_path)
        loaded = load_sparse_corpus(persist_dir=tmp_path)
        assert loaded == []
