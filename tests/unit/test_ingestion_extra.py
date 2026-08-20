"""文档摄入模块补充测试.

覆盖 rag/ingestion.py 的 build_parent_documents / _enrich_chunk_metadata /
_stable_parent_id / split_documents (无 LLM 模式).
"""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.ingestion import (
    _enrich_chunk_metadata,
    _stable_parent_id,
    build_parent_documents,
    split_documents,
)


# ---------------------------------------------------------------------------
# _stable_parent_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStableParentId:
    """稳定 parent_id 生成测试."""

    def test_deterministic_output(self):
        """相同输入应产生相同 ID."""
        pid1 = _stable_parent_id(source="doc.md", section_path="FRTB", start_char=0, page=0)
        pid2 = _stable_parent_id(source="doc.md", section_path="FRTB", start_char=0, page=0)
        assert pid1 == pid2

    def test_different_inputs_produce_different_ids(self):
        """不同输入应产生不同 ID."""
        pid1 = _stable_parent_id(source="a.md", section_path="x", start_char=0, page=0)
        pid2 = _stable_parent_id(source="b.md", section_path="x", start_char=0, page=0)
        assert pid1 != pid2

    def test_id_length_12(self):
        """ID 应为 12 字符 (sha1 前 12 位)."""
        pid = _stable_parent_id(source="s", section_path="p", start_char=1, page=2)
        assert len(pid) == 12


# ---------------------------------------------------------------------------
# build_parent_documents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildParentDocuments:
    """从原始文档构建 parent documents 测试."""

    def test_markdown_with_sections(self):
        """Markdown 文档应按 section 切分为 parent."""
        content = "# FRTB\n\nOverview content.\n\n## Delta\n\nDelta risk content.\n"
        docs = [Document(page_content=content, metadata={"source": "doc.md", "file_type": "md"})]
        parents = build_parent_documents(docs)
        assert len(parents) >= 1
        for p in parents:
            assert p.metadata["parent_id"]
            assert p.metadata["parent_type"] in ("md_section", "md_file")

    def test_markdown_without_sections(self):
        """无标题的 Markdown 仍按 section 解析 (每个文本块为一个 section)."""
        content = "Just plain text without headings."
        docs = [Document(page_content=content, metadata={"source": "doc.md", "file_type": "md"})]
        parents = build_parent_documents(docs)
        assert len(parents) >= 1
        # parent_type 应为 md_section 或 md_file
        assert parents[0].metadata["parent_type"] in ("md_section", "md_file")

    def test_pdf_page_parent(self):
        """PDF 文档应按 page 构建 parent."""
        docs = [Document(page_content="page content", metadata={"source": "doc.pdf", "file_type": "pdf", "page": 1})]
        parents = build_parent_documents(docs)
        assert len(parents) == 1
        assert parents[0].metadata["parent_type"] == "pdf_page"

    def test_generic_doc_parent(self):
        """非 Markdown/PDF 文档应作为 doc 类型."""
        docs = [Document(page_content="text", metadata={"source": "doc.docx", "file_type": "docx", "page": 0})]
        parents = build_parent_documents(docs)
        assert len(parents) == 1
        assert parents[0].metadata["parent_type"] == "doc"

    def test_empty_content_skipped(self):
        """空 section 文本应被跳过."""
        content = "# Section\n\n   \n\n## Other\n\nReal content."
        docs = [Document(page_content=content, metadata={"source": "doc.md", "file_type": "md"})]
        parents = build_parent_documents(docs)
        # 应至少有一个 parent (非空 section)
        assert len(parents) >= 1
        assert all(p.page_content.strip() for p in parents)

    def test_multiple_docs(self):
        """多文档应分别处理."""
        docs = [
            Document(page_content="# A\n\ntext A", metadata={"source": "a.md", "file_type": "md"}),
            Document(page_content="# B\n\ntext B", metadata={"source": "b.md", "file_type": "md"}),
        ]
        parents = build_parent_documents(docs)
        assert len(parents) >= 2


# ---------------------------------------------------------------------------
# _enrich_chunk_metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnrichChunkMetadata:
    """chunk 元数据丰富测试."""

    def test_adds_chunk_id_and_index(self):
        """应添加 chunk_id 和 chunk_index."""
        chunks = [Document(page_content="text", metadata={"source": "doc.md"})]
        _enrich_chunk_metadata(chunks)
        assert "chunk_id" in chunks[0].metadata
        assert chunks[0].metadata["chunk_index"] == 0

    def test_chunk_id_includes_source_filename(self):
        """有 source 时 chunk_id 应包含文件名."""
        chunks = [Document(page_content="x", metadata={"source": "path/to/doc.md"})]
        _enrich_chunk_metadata(chunks)
        assert "doc.md" in chunks[0].metadata["chunk_id"]

    def test_chunk_id_without_source(self):
        """无 source 时 chunk_id 为纯 hash."""
        chunks = [Document(page_content="x", metadata={})]
        _enrich_chunk_metadata(chunks)
        cid = chunks[0].metadata["chunk_id"]
        assert ":" not in cid

    def test_invalid_start_index_handled_internally(self):
        """非法 start_index 在内部计算时默认为 0 (不回写 metadata)."""
        chunks = [Document(page_content="x", metadata={"source": "s", "start_index": "abc"})]
        _enrich_chunk_metadata(chunks)
        # metadata 中 start_index 可能仍是原值, 但 chunk_id 和 parent_id 应正常生成
        assert "chunk_id" in chunks[0].metadata
        assert "chunk_index" in chunks[0].metadata

    def test_parent_id_generated_when_missing(self):
        """缺失 parent_id 时应自动生成."""
        chunks = [Document(page_content="x", metadata={"source": "doc.md", "parent_id": ""})]
        _enrich_chunk_metadata(chunks)
        assert chunks[0].metadata["parent_id"]

    def test_section_start_char_adds_to_start_index(self):
        """有 section_start_char 时应加到 start_index."""
        chunks = [
            Document(
                page_content="x",
                metadata={"source": "doc.md", "start_index": 10, "section_start_char": 100},
            )
        ]
        _enrich_chunk_metadata(chunks)
        assert chunks[0].metadata["start_index"] == 110

    def test_markdown_line_range_computed(self):
        """Markdown chunk 有 _source_text 时应计算 line range."""
        source_text = "line1\nline2\nline3\nline4"
        chunks = [
            Document(
                page_content="line2",
                metadata={"source": "doc.md", "file_type": "md", "_source_text": source_text, "start_index": 6},
            )
        ]
        _enrich_chunk_metadata(chunks)
        assert "start_line" in chunks[0].metadata
        assert "end_line" in chunks[0].metadata


# ---------------------------------------------------------------------------
# split_documents (无 LLM 模式)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSplitDocumentsNoLlm:
    """split_documents (use_llm_chunking=False) 测试."""

    def test_splits_simple_text(self):
        """应切分简单文本."""
        docs = [Document(page_content="a" * 2000, metadata={"source": "doc.md"})]
        chunks = split_documents(docs, use_llm_chunking=False, max_chunk_size=500, overlap=50)
        assert len(chunks) >= 2

    def test_markdown_section_enrichment(self):
        """Markdown 应先做 section 丰富."""
        content = "# Title\n\nSome sufficiently long content here to pass the min-chunk filter threshold of thirty chars.\n"
        docs = [Document(page_content=content, metadata={"source": "doc.md", "file_type": "md"})]
        chunks = split_documents(docs, use_llm_chunking=False, max_chunk_size=800, overlap=50)
        assert len(chunks) >= 1
        assert "chunk_id" in chunks[0].metadata

    def test_empty_docs_returns_empty(self):
        """空文档列表返回空."""
        assert split_documents([], use_llm_chunking=False) == []

    def test_short_fragments_filtered(self):
        """过短碎片 (<30 字符) 应被过滤, 不进入索引."""
        docs = [Document(page_content="tiny fragment", metadata={"source": "doc.md"})]
        chunks = split_documents(docs, use_llm_chunking=False, max_chunk_size=800, overlap=50)
        assert chunks == []

    def test_preserves_metadata(self):
        """切分后应保留原始元数据."""
        docs = [
            Document(
                page_content="text content long enough to survive the minimum chunk size filter",
                metadata={"source": "doc.md", "custom": "value"},
            )
        ]
        chunks = split_documents(docs, use_llm_chunking=False, max_chunk_size=800, overlap=50)
        assert chunks[0].metadata.get("source") == "doc.md"
        assert chunks[0].metadata.get("custom") == "value"
