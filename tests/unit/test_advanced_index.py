"""高级索引 (Parent / Summary / HyDE) 的单元测试.

覆盖 rag/advanced_index.py 的全部纯函数: 语料构建、摘要抽取、HyDE 问题生成、
JSONL 持久化与统计.
"""

from __future__ import annotations

import pathlib

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.advanced_index import (
    PARENT_CORPUS_FILENAME,
    SUMMARY_CORPUS_FILENAME,
    HYDE_CORPUS_FILENAME,
    _extractive_summary,
    _hyde_question,
    advanced_index_stats,
    build_hyde_docs,
    build_summary_docs,
    load_hyde_corpus,
    load_parent_corpus,
    load_summary_corpus,
    parent_corpus_by_id,
    persist_hyde_corpus,
    persist_parent_corpus,
    persist_summary_corpus,
)


# ---------------------------------------------------------------------------
# _extractive_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractiveSummary:
    """摘要抽取逻辑测试."""

    def test_empty_text_returns_empty(self):
        """空文本应返回空字符串."""
        assert _extractive_summary("") == ""
        assert _extractive_summary("   ") == ""
        assert _extractive_summary(None) == ""

    def test_short_text_returns_head(self):
        """短文本直接取前几行拼接."""
        text = "# Title\n\nSome short content here.\n"
        result = _extractive_summary(text)
        assert "Title" in result
        assert "short content" in result

    def test_long_text_truncated_to_max_chars(self):
        """长文本应截断到 max_chars."""
        text = " ".join(["word"] * 500)
        result = _extractive_summary(text, max_chars=100)
        assert len(result) <= 100

    def test_sentence_based_fallback(self):
        """当行数不足时按句子拼接."""
        text = (
            "This is a very long sentence that contains enough characters to be kept. "
            "Another sentence with sufficient length to be included in the summary output."
        )
        result = _extractive_summary(text, max_chars=200)
        assert result  # 非空
        assert len(result) <= 200

    def test_short_sentences_skipped(self):
        """短于 30 字符的句子在句子模式中被跳过."""
        text = "ok. hi. This is a long enough sentence to be kept in the output summary."
        result = _extractive_summary(text, max_chars=300)
        assert "long enough" in result


# ---------------------------------------------------------------------------
# _hyde_question
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHydeQuestion:
    """HyDE 假设性问题生成测试."""

    def test_with_section_path(self):
        """有 section_path 时应提取末段作为主题."""
        text = "The delta approach measures sensitivity to small changes in underlying risk factors."
        q = _hyde_question(text, section_path="Market Risk/Delta Approach")
        assert "Delta Approach" in q
        assert "What is" in q

    def test_without_section_path_with_keywords(self):
        """无 section_path 但有英文关键词时使用关键词."""
        text = "Value at risk is a statistical measure of downside exposure."
        q = _hyde_question(text, section_path="")
        assert q
        assert "Value" in q or "risk" in q

    def test_empty_text_returns_default(self):
        """空文本且无关键词时返回默认问题."""
        q = _hyde_question("", section_path="")
        assert q == "What is the definition and background"


# ---------------------------------------------------------------------------
# build_summary_docs / build_hyde_docs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildDocs:
    """从 parent 文档构建 summary / hyde 文档."""

    def _make_parents(self) -> list[Document]:
        return [
            Document(
                page_content="# FRTB\n\nThe Fundamental Review of the Trading Book is a Basel framework.",
                metadata={"parent_id": "p1", "section_path": "FRTB/Overview"},
            ),
            Document(
                page_content="Delta risk measures sensitivity to underlying factors.",
                metadata={"parent_id": "p2", "section_path": "Market Risk/Delta"},
            ),
        ]

    def test_build_summary_docs_produces_summaries(self):
        """summary 文档应包含 parent_id 并标注 doc_type."""
        parents = self._make_parents()
        summaries = build_summary_docs(parents)
        assert len(summaries) == 2
        assert all(s.metadata["doc_type"] == "summary" for s in summaries)
        assert summaries[0].metadata["parent_id"] == "p1"

    def test_build_summary_docs_skips_missing_parent_id(self):
        """无 parent_id 的文档应被跳过."""
        parents = [Document(page_content="no id", metadata={})]
        assert build_summary_docs(parents) == []

    def test_build_hyde_docs_produces_questions(self):
        """hyde 文档应包含假设性问题."""
        parents = self._make_parents()
        hydes = build_hyde_docs(parents)
        assert len(hydes) == 2
        assert all(h.metadata["doc_type"] == "hyde" for h in hydes)
        assert "What is" in hydes[0].page_content

    def test_build_hyde_docs_skips_missing_parent_id(self):
        """无 parent_id 的文档应被跳过."""
        parents = [Document(page_content="no id", metadata={})]
        assert build_hyde_docs(parents) == []


# ---------------------------------------------------------------------------
# 持久化: persist / load round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPersistLoad:
    """JSONL 持久化往返测试."""

    def test_parent_corpus_roundtrip(self, tmp_path: pathlib.Path):
        """parent 语料写入后应能完整读回."""
        parents = [
            Document(page_content="parent A", metadata={"parent_id": "a"}),
            Document(page_content="parent B", metadata={"parent_id": "b"}),
        ]
        path = persist_parent_corpus(parents=parents, persist_dir=tmp_path)
        assert pathlib.Path(path).exists()
        assert pathlib.Path(path).name == PARENT_CORPUS_FILENAME

        loaded = load_parent_corpus(persist_dir=tmp_path)
        assert len(loaded) == 2
        assert loaded[0].page_content == "parent A"
        assert loaded[0].metadata["parent_id"] == "a"

    def test_load_parent_corpus_missing_dir_returns_empty(self, tmp_path: pathlib.Path):
        """目录不存在时读取返回空列表."""
        assert load_parent_corpus(persist_dir=tmp_path / "nope") == []

    def test_summary_corpus_roundtrip(self, tmp_path: pathlib.Path):
        """summary 语料往返."""
        parents = [
            Document(page_content="x", metadata={"parent_id": "p1", "section_path": "s"}),
        ]
        persist_summary_corpus(parents=parents, persist_dir=tmp_path)
        loaded = load_summary_corpus(persist_dir=tmp_path)
        assert len(loaded) == 1
        assert loaded[0].metadata["doc_type"] == "summary"

    def test_hyde_corpus_roundtrip(self, tmp_path: pathlib.Path):
        """hyde 语料往返."""
        parents = [
            Document(page_content="x", metadata={"parent_id": "p1", "section_path": "s"}),
        ]
        persist_hyde_corpus(parents=parents, persist_dir=tmp_path)
        loaded = load_hyde_corpus(persist_dir=tmp_path)
        assert len(loaded) == 1
        assert loaded[0].metadata["doc_type"] == "hyde"

    def test_load_summary_corpus_missing_returns_empty(self, tmp_path: pathlib.Path):
        """summary 文件不存在时返回空."""
        assert load_summary_corpus(persist_dir=tmp_path) == []

    def test_load_hyde_corpus_missing_returns_empty(self, tmp_path: pathlib.Path):
        """hyde 文件不存在时返回空."""
        assert load_hyde_corpus(persist_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# parent_corpus_by_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParentCorpusById:
    """按 parent_id 索引 parent 语料."""

    def test_builds_id_map(self, tmp_path: pathlib.Path):
        """应构建 parent_id -> Document 映射."""
        parents = [
            Document(page_content="A", metadata={"parent_id": "a"}),
            Document(page_content="B", metadata={"parent_id": "b"}),
            Document(page_content="no id", metadata={}),
        ]
        persist_parent_corpus(parents=parents, persist_dir=tmp_path)
        result = parent_corpus_by_id(persist_dir=tmp_path)
        assert "a" in result
        assert "b" in result
        assert result["a"].page_content == "A"

    def test_empty_when_no_file(self, tmp_path: pathlib.Path):
        """文件不存在时返回空字典."""
        assert parent_corpus_by_id(persist_dir=tmp_path) == {}


# ---------------------------------------------------------------------------
# advanced_index_stats
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAdvancedIndexStats:
    """高级索引统计."""

    def test_stats_includes_counts_and_paths(self, tmp_path: pathlib.Path):
        """统计应包含 parents/summaries/hydes 计数与文件路径."""
        parents = [
            Document(page_content="x", metadata={"parent_id": "p1", "section_path": "s"}),
        ]
        persist_parent_corpus(parents=parents, persist_dir=tmp_path)
        persist_summary_corpus(parents=parents, persist_dir=tmp_path)
        persist_hyde_corpus(parents=parents, persist_dir=tmp_path)

        stats = advanced_index_stats(persist_dir=tmp_path)
        assert stats["parents"] == 1
        assert stats["summaries"] == 1
        assert stats["hydes"] == 1
        assert SUMMARY_CORPUS_FILENAME in stats["summary_path"]
        assert HYDE_CORPUS_FILENAME in stats["hyde_path"]
        assert PARENT_CORPUS_FILENAME in stats["parent_path"]

    def test_stats_empty_when_no_files(self, tmp_path: pathlib.Path):
        """无文件时统计全为 0."""
        stats = advanced_index_stats(persist_dir=tmp_path)
        assert stats["parents"] == 0
        assert stats["summaries"] == 0
        assert stats["hydes"] == 0
