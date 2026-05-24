"""Unit tests for RAG source loader."""

from __future__ import annotations

import pathlib

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.source_loader import load_sources


# ---------------------------------------------------------------------------
# Loading Markdown files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadMarkdown:
    """Tests for loading Markdown files."""

    def test_loads_single_markdown_file(self, tmp_path):
        """Should load a single .md file and return Document list."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\nSome content about FRTB.\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert len(docs) == 1
        assert "FRTB" in docs[0].page_content
        assert docs[0].metadata["source"] == str(md_file)
        assert docs[0].metadata["file_type"] == "md"

    def test_skips_readme_md(self, tmp_path):
        """Should skip README.md files."""
        readme = tmp_path / "README.md"
        readme.write_text("# README\n\nThis should be skipped.\n", encoding="utf-8")
        content = tmp_path / "content.md"
        content.write_text("# Content\n\nActual content.\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert len(docs) == 1
        assert "Actual content" in docs[0].page_content

    def test_markdown_content_preserved(self, tmp_path):
        """Full markdown content including headings should be preserved."""
        md_file = tmp_path / "full.md"
        text = "# Section 1\n\nParagraph one.\n\n## Section 1.1\n\nParagraph two.\n"
        md_file.write_text(text, encoding="utf-8")

        docs = load_sources(tmp_path)
        assert "Section 1" in docs[0].page_content
        assert "Paragraph two" in docs[0].page_content


# ---------------------------------------------------------------------------
# Loading from directory with multiple files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadMultipleFiles:
    """Tests for loading multiple files from a directory."""

    def test_loads_multiple_md_files(self, tmp_path):
        """Should load all .md files recursively."""
        (tmp_path / "a.md").write_text("# Doc A\n\nContent A.\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("# Doc B\n\nContent B.\n", encoding="utf-8")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "c.md").write_text("# Doc C\n\nContent C.\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert len(docs) == 3
        sources = {d.metadata["source"] for d in docs}
        assert str(tmp_path / "a.md") in sources
        assert str(sub / "c.md") in sources

    def test_sorted_loading_order(self, tmp_path):
        """Files should be loaded in sorted order."""
        (tmp_path / "z_file.md").write_text("# Z\n\nZ content.\n", encoding="utf-8")
        (tmp_path / "a_file.md").write_text("# A\n\nA content.\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        sources = [d.metadata["source"] for d in docs]
        # Sorted means a_file before z_file
        assert "a_file.md" in sources[0]
        assert "z_file.md" in sources[1]


# ---------------------------------------------------------------------------
# Empty file handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmptyFileHandling:
    """Tests for handling empty files."""

    def test_empty_file_still_loaded(self, tmp_path):
        """An empty .md file should still produce a Document (with empty content)."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert len(docs) == 1
        assert docs[0].page_content == ""

    def test_nonexistent_directory_returns_empty(self):
        """A non-existent directory should return an empty list."""
        fake_dir = pathlib.Path("/tmp/nonexistent_corpus_xyz_123456")
        docs = load_sources(fake_dir)
        assert docs == []


# ---------------------------------------------------------------------------
# Encoding handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEncodingHandling:
    """Tests for file encoding handling."""

    def test_utf8_content_loaded_correctly(self, tmp_path):
        """UTF-8 encoded content with Chinese characters should load properly."""
        md_file = tmp_path / "chinese.md"
        md_file.write_text("# 风险管理\n\nFRTB标准法资本计提。\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert "风险管理" in docs[0].page_content
        assert "FRTB标准法" in docs[0].page_content

    def test_file_with_special_chars(self, tmp_path):
        """Files with special unicode characters should be handled gracefully."""
        md_file = tmp_path / "special.md"
        content = "# Formulas\n\nΔ (delta) × exposure = risk charge\n"
        md_file.write_text(content, encoding="utf-8")

        docs = load_sources(tmp_path)
        assert "Δ" in docs[0].page_content


# ---------------------------------------------------------------------------
# Unsupported format handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnsupportedFormat:
    """Tests for unsupported file format handling."""

    def test_unsupported_extension_skipped(self, tmp_path):
        """Files with unsupported extensions should be silently skipped."""
        (tmp_path / "data.csv").write_text("col1,col2\n1,2\n", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        (tmp_path / "valid.md").write_text("# Valid\n\nContent.\n", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert len(docs) == 1
        assert "Valid" in docs[0].page_content

    def test_no_supported_files_returns_empty(self, tmp_path):
        """A directory with only unsupported files returns empty list."""
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "script.py").write_text("print('hi')", encoding="utf-8")

        docs = load_sources(tmp_path)
        assert docs == []
