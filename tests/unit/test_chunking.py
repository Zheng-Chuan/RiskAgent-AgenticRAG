"""文档切割模块单元测试.

覆盖 rag/chunking.py 的 fallback 切割、LLM 语义切割 (mock)、chunk 文档构建.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.chunking import (
    _build_chunk_doc,
    _fallback_chunking,
    _llm_semantic_chunking,
    llm_semantic_split_document,
)


# ---------------------------------------------------------------------------
# _fallback_chunking
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFallbackChunking:
    """传统字符切割 fallback 测试."""

    def test_short_text_single_chunk(self):
        """短文本 (overlap=0) 应返回单个 chunk."""
        chunks = _fallback_chunking("hello world this is a test", max_chunk_size=800, overlap=0)
        assert len(chunks) == 1
        assert "hello" in chunks[0]["text"]
        assert chunks[0]["reason"] == "fallback_boundary"

    def test_empty_text_returns_empty(self):
        """空文本返回空列表."""
        assert _fallback_chunking("", max_chunk_size=800, overlap=100) == []

    def test_whitespace_only_skipped(self):
        """纯空白文本应被跳过."""
        chunks = _fallback_chunking("   \n   ", max_chunk_size=800, overlap=100)
        assert chunks == []

    def test_long_text_split_into_multiple(self):
        """长文本应被切分为多个 chunk."""
        text = "word " * 500  # ~2500 chars
        chunks = _fallback_chunking(text, max_chunk_size=800, overlap=100)
        assert len(chunks) >= 2
        # 每个 chunk 应有 start/end
        for c in chunks:
            assert "start" in c
            assert "end" in c
            assert c["text"].strip()

    def test_paragraph_boundary_preferred(self):
        """应优先在段落边界切割."""
        text = "First paragraph.\n\nSecond paragraph that is long enough to be its own chunk."
        chunks = _fallback_chunking(text, max_chunk_size=40, overlap=10)
        assert len(chunks) >= 1
        # 第一个 chunk 应在段落边界结束
        assert "First paragraph" in chunks[0]["text"]


# ---------------------------------------------------------------------------
# _build_chunk_doc
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildChunkDoc:
    """chunk Document 构建测试."""

    def test_builds_doc_with_metadata(self):
        """应构建带 chunking 元数据的 Document."""
        chunk_data = {"text": "chunk content", "start": 0, "end": 13, "reason": "boundary", "summary": "sum"}
        meta = {"source": "doc.md", "parent_id": "p1"}
        doc = _build_chunk_doc(chunk_data, meta, "p1", "section/path")
        assert doc is not None
        assert doc.page_content == "chunk content"
        assert doc.metadata["chunking_method"] == "llm_semantic"
        assert doc.metadata["parent_id"] == "p1"
        assert doc.metadata["section_path"] == "section/path"
        assert doc.metadata["chunk_reason"] == "boundary"
        assert doc.metadata["start_index"] == 0

    def test_empty_chunk_returns_none(self):
        """空文本 chunk 应返回 None."""
        chunk_data = {"text": "   ", "start": 0, "end": 0}
        assert _build_chunk_doc(chunk_data, {}, "p", "s") is None

    def test_missing_fields_use_defaults(self):
        """缺失字段应使用默认值."""
        chunk_data = {"text": "x"}
        doc = _build_chunk_doc(chunk_data, {}, "p", "")
        assert doc is not None
        assert doc.metadata["chunk_reason"] == ""
        assert doc.metadata["start_index"] == 0


# ---------------------------------------------------------------------------
# _llm_semantic_chunking (mock LLM)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLlmSemanticChunking:
    """LLM 语义切割测试 (mock LLM 调用)."""

    def test_short_text_returns_single_chunk(self):
        """短文本应直接返回单 chunk, 不调用 LLM."""
        result = _llm_semantic_chunking("short text", max_chunk_size=800, overlap=100)
        assert len(result) == 1
        assert result[0]["text"] == "short text"
        assert result[0]["reason"] == "short_text"

    def test_empty_text_returns_single_empty_chunk(self):
        """空文本返回单 chunk."""
        result = _llm_semantic_chunking("", max_chunk_size=800, overlap=100)
        assert len(result) == 1

    def test_llm_returns_chunks(self):
        """LLM 返回有效 chunks 时应被正确解析."""
        long_text = "sentence one. " * 200  # > max_chunk_size
        fake_response = {
            "chunks": [
                {"start": 0, "end": 50, "reason": "para", "summary": "s1"},
                {"start": 50, "end": 100, "reason": "para", "summary": "s2"},
            ],
            "total_chunks": 2,
        }
        with patch("riskagent_agenticrag.rag.chunking.call_llm_json_with_model", return_value=fake_response):
            result = _llm_semantic_chunking(long_text, max_chunk_size=800, overlap=100)
        assert len(result) == 2
        assert result[0]["reason"] == "para"

    def test_llm_returns_empty_falls_back(self):
        """LLM 返回空 chunks 时应回退到 fallback."""
        long_text = "word " * 500
        with patch("riskagent_agenticrag.rag.chunking.call_llm_json_with_model", return_value={"chunks": []}):
            result = _llm_semantic_chunking(long_text, max_chunk_size=800, overlap=100)
        # 应回退到 fallback 切割
        assert len(result) >= 1
        assert all(r["reason"] == "fallback_boundary" for r in result)

    def test_llm_exception_falls_back(self):
        """LLM 调用异常时应回退."""
        long_text = "word " * 500
        with patch("riskagent_agenticrag.rag.chunking.call_llm_json_with_model", side_effect=RuntimeError("boom")):
            result = _llm_semantic_chunking(long_text, max_chunk_size=800, overlap=100)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# llm_semantic_split_document
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLlmSemanticSplitDocument:
    """单文档 LLM 语义切割测试."""

    def test_empty_content_returns_empty(self):
        """空内容返回空列表."""
        doc = Document(page_content="", metadata={})
        assert llm_semantic_split_document(doc) == []

    def test_short_content_returns_chunks(self):
        """短内容应直接走 _llm_semantic_chunking."""
        doc = Document(page_content="short text", metadata={"parent_id": "p1", "section_path": "s"})
        result = llm_semantic_split_document(doc)
        assert len(result) == 1
        assert result[0].metadata["parent_id"] == "p1"

    def test_long_content_uses_coarse_split(self):
        """长内容 (>8000 字符) 应先粗切再 LLM 精切."""
        long_text = "paragraph text here. " * 500  # ~10000 chars
        doc = Document(page_content=long_text, metadata={"parent_id": "p1", "section_path": "s"})
        # mock LLM 返回空 chunks 触发 fallback
        with patch("riskagent_agenticrag.rag.chunking.call_llm_json_with_model", return_value={"chunks": []}):
            result = llm_semantic_split_document(doc, max_chunk_size=800, overlap=100)
        assert len(result) >= 1
        assert all(d.metadata.get("parent_id") == "p1" for d in result)
