"""RAG pipeline citations 提取测试.

覆盖 rag/pipeline.py 的 extract_citations 各种元数据组合.
"""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.pipeline import extract_citations


@pytest.mark.unit
class TestExtractCitations:
    """extract_citations 行为测试."""

    def test_empty_docs_returns_empty_list(self):
        """空文档列表应返回空 citations."""
        assert extract_citations([]) == []

    def test_basic_source_and_chunk_id(self):
        """应提取 source 和 chunk_id."""
        docs = [Document(page_content="content", metadata={"source": "doc.md", "chunk_id": "c1"})]
        result = extract_citations(docs)
        assert len(result) == 1
        assert result[0]["source"] == "doc.md"
        assert result[0]["chunk_id"] == "c1"

    def test_includes_snippet_from_content(self):
        """应从 page_content 截取 snippet (最多 300 字符)."""
        long_text = "x" * 500
        docs = [Document(page_content=long_text, metadata={"source": "s", "chunk_id": "c"})]
        result = extract_citations(docs)
        assert "snippet" in result[0]
        assert len(result[0]["snippet"]) == 300

    def test_start_index_when_present(self):
        """有 start_index 时应作为整数包含."""
        docs = [Document(page_content="t", metadata={"source": "s", "chunk_id": "c", "start_index": 42})]
        result = extract_citations(docs)
        assert result[0]["start_index"] == 42

    def test_start_index_invalid_skipped(self):
        """start_index 非法时应静默跳过."""
        docs = [Document(page_content="t", metadata={"source": "s", "chunk_id": "c", "start_index": "abc"})]
        result = extract_citations(docs)
        assert "start_index" not in result[0]

    def test_section_path_included(self):
        """有 section_path 时应包含."""
        docs = [Document(page_content="t", metadata={"source": "s", "chunk_id": "c", "section_path": "Risk/Delta"})]
        result = extract_citations(docs)
        assert result[0]["section_path"] == "Risk/Delta"

    def test_page_included_when_int(self):
        """page 为整数时应包含."""
        docs = [Document(page_content="t", metadata={"source": "s", "chunk_id": "c", "page": 3})]
        result = extract_citations(docs)
        assert result[0]["page"] == 3

    def test_start_and_end_line(self):
        """有 start_line / end_line 时应包含."""
        docs = [Document(page_content="t", metadata={"source": "s", "chunk_id": "c", "start_line": 10, "end_line": 20})]
        result = extract_citations(docs)
        assert result[0]["start_line"] == 10
        assert result[0]["end_line"] == 20

    def test_expanded_text_used_for_snippet(self):
        """有 expanded_text 时 snippet 应优先使用它."""
        docs = [
            Document(
                page_content="original",
                metadata={"source": "s", "chunk_id": "c", "expanded_text": "expanded version"},
            )
        ]
        result = extract_citations(docs)
        assert result[0]["snippet"] == "expanded version"

    def test_missing_metadata_defaults_to_empty_strings(self):
        """无元数据时 source/chunk_id 应为空字符串."""
        docs = [Document(page_content="t", metadata={})]
        result = extract_citations(docs)
        assert result[0]["source"] == ""
        assert result[0]["chunk_id"] == ""

    def test_multiple_docs(self):
        """多个文档应生成多个 citations."""
        docs = [
            Document(page_content="a", metadata={"source": "1", "chunk_id": "1"}),
            Document(page_content="b", metadata={"source": "2", "chunk_id": "2"}),
        ]
        result = extract_citations(docs)
        assert len(result) == 2
        assert result[0]["source"] == "1"
        assert result[1]["source"] == "2"
