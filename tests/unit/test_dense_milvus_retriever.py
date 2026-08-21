"""DenseMilvusRetriever 单元测试 -- 覆盖 invoke 方法与空查询处理."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from riskagent_agenticrag.rag.dense_milvus_retriever import (
    DenseMilvusRetriever,
    DenseMilvusRetrieverConfig,
)


@pytest.mark.unit
class TestDenseMilvusRetrieverConfig:
    """DenseMilvusRetrieverConfig 数据类测试."""

    def test_default_k(self):
        cfg = DenseMilvusRetrieverConfig()
        assert cfg.k == 30

    def test_custom_k(self):
        cfg = DenseMilvusRetrieverConfig(k=10)
        assert cfg.k == 10


@pytest.mark.unit
class TestDenseMilvusRetrieverInvoke:
    """DenseMilvusRetriever.invoke 方法测试."""

    def _make_retriever(self, tmp_path: Path):
        """构建带 mock 依赖的 DenseMilvusRetriever."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 8
        mock_client = MagicMock()
        with patch("riskagent_agenticrag.rag.dense_milvus_retriever.build_embeddings", return_value=mock_embeddings), \
             patch("riskagent_agenticrag.rag.dense_milvus_retriever.build_milvus_client", return_value=mock_client), \
             patch("riskagent_agenticrag.rag.dense_milvus_retriever.ensure_collection"):
            retriever = DenseMilvusRetriever(
                persist_dir=tmp_path,
                config=DenseMilvusRetrieverConfig(k=5),
            )
        retriever._client = mock_client
        retriever._embeddings = mock_embeddings
        return retriever, mock_client, mock_embeddings

    def test_invoke_returns_documents_from_search(self, tmp_path: Path):
        """invoke 应把 search 结果转为 Document 列表."""
        retriever, mock_client, mock_embeddings = self._make_retriever(tmp_path)
        with patch("riskagent_agenticrag.rag.dense_milvus_retriever.search") as mock_search:
            mock_search.return_value = [
                {"chunk_id": "c1", "source": "a.md", "text": "FRTB content",
                 "file_type": "md", "parent_id": "p1", "section_path": "sec",
                 "context_brief": "brief", "start_index": 0, "page": 1,
                 "start_line": 0, "end_line": 10, "score": 0.95},
            ]
            docs = retriever.invoke("what is FRTB")
        assert len(docs) == 1
        doc = docs[0]
        assert doc.page_content == "FRTB content"
        assert doc.metadata["chunk_id"] == "c1"
        assert doc.metadata["source"] == "a.md"
        assert doc.metadata["dense_rank"] == 1
        assert doc.metadata["dense_score"] == 0.95

    def test_invoke_empty_query_returns_empty(self, tmp_path: Path):
        """空查询应返回空列表."""
        retriever, _, _ = self._make_retriever(tmp_path)
        docs = retriever.invoke("")
        assert docs == []

    def test_invoke_whitespace_query_returns_empty(self, tmp_path: Path):
        """纯空白查询应返回空列表."""
        retriever, _, _ = self._make_retriever(tmp_path)
        docs = retriever.invoke("   ")
        assert docs == []

    def test_invoke_without_score_omits_dense_score(self, tmp_path: Path):
        """search 结果无 score 字段时, metadata 不应包含 dense_score."""
        retriever, _, _ = self._make_retriever(tmp_path)
        with patch("riskagent_agenticrag.rag.dense_milvus_retriever.search") as mock_search:
            mock_search.return_value = [
                {"chunk_id": "c1", "source": "a.md", "text": "content", "score": None},
            ]
            docs = retriever.invoke("query")
        assert len(docs) == 1
        assert "dense_score" not in docs[0].metadata

    def test_invoke_multiple_docs_ranks_sequentially(self, tmp_path: Path):
        """多个结果应按顺序编号 dense_rank."""
        retriever, _, _ = self._make_retriever(tmp_path)
        with patch("riskagent_agenticrag.rag.dense_milvus_retriever.search") as mock_search:
            mock_search.return_value = [
                {"chunk_id": "c1", "source": "a.md", "text": "first"},
                {"chunk_id": "c2", "source": "b.md", "text": "second"},
                {"chunk_id": "c3", "source": "c.md", "text": "third"},
            ]
            docs = retriever.invoke("query")
        assert len(docs) == 3
        assert docs[0].metadata["dense_rank"] == 1
        assert docs[1].metadata["dense_rank"] == 2
        assert docs[2].metadata["dense_rank"] == 3

    def test_invoke_missing_fields_use_defaults(self, tmp_path: Path):
        """search 结果缺少字段时应使用默认值, 不抛异常."""
        retriever, _, _ = self._make_retriever(tmp_path)
        with patch("riskagent_agenticrag.rag.dense_milvus_retriever.search") as mock_search:
            mock_search.return_value = [
                {},  # 完全空的字典
            ]
            docs = retriever.invoke("query")
        assert len(docs) == 1
        assert docs[0].page_content == ""
        assert docs[0].metadata["chunk_id"] == ""
        assert docs[0].metadata["start_index"] == 0
        assert docs[0].metadata["page"] == 0
