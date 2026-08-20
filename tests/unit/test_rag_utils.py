"""RAG 共享工具函数测试.

覆盖 rag/utils.py: tokenize / token_set / doc_key / rrf_scores / JSONL 读写.
"""

from __future__ import annotations

import pathlib

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.utils import (
    doc_key,
    load_docs_jsonl,
    persist_docs_jsonl,
    rrf_scores,
    tokenize,
    token_set,
)


# ---------------------------------------------------------------------------
# tokenize / token_set
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTokenize:
    """分词函数测试."""

    def test_english_lowercase(self):
        """英文应转小写."""
        assert tokenize("Hello WORLD") == ["hello", "world"]

    def test_chinese_kept(self):
        """中文应保留为整块."""
        tokens = tokenize("风险 管理")
        assert "风险" in tokens
        assert "管理" in tokens

    def test_mixed_alphanumeric(self):
        """中英文数字混合应正确分词 (中英文相邻时作为一个 token)."""
        tokens = tokenize("FRTB 标准法 capital 1234")
        assert "frtb" in tokens
        assert "标准法" in tokens
        assert "capital" in tokens
        assert "1234" in tokens

    def test_empty_string(self):
        """空字符串返回空列表."""
        assert tokenize("") == []
        assert tokenize(None) == []

    def test_punctuation_excluded(self):
        """标点应被移除."""
        tokens = tokenize("hello, world!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "," not in tokens


@pytest.mark.unit
class TestTokenSet:
    """token_set 去重测试."""

    def test_dedup(self):
        """应去重."""
        s = token_set("hello hello world")
        assert s == {"hello", "world"}

    def test_empty(self):
        """空输入返回空集合."""
        assert token_set("") == set()


# ---------------------------------------------------------------------------
# doc_key
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocKey:
    """Document 去重键测试."""

    def test_with_source_and_chunk_id(self):
        """有 source + chunk_id 时用 source::chunk_id."""
        d = Document(page_content="x", metadata={"source": "doc.md", "chunk_id": "c1"})
        assert doc_key(d) == "doc.md::c1"

    def test_without_chunk_id_falls_back_to_hash(self):
        """无 chunk_id 时回退到 content hash."""
        d = Document(page_content="unique content", metadata={"source": "doc.md"})
        key = doc_key(d)
        assert key != "doc.md"
        assert key  # 非空

    def test_empty_metadata(self):
        """无元数据时用 content hash."""
        d = Document(page_content="some text", metadata={})
        assert doc_key(d)


# ---------------------------------------------------------------------------
# rrf_scores
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRrfScores:
    """RRF 融合测试."""

    def test_single_list(self):
        """单路排序应给第一名最高分."""
        scores = rrf_scores(ranked_lists=[["a", "b", "c"]])
        assert scores["a"] > scores["b"] > scores["c"]

    def test_multiple_lists_aggregate(self):
        """多路应聚合分数."""
        scores = rrf_scores(ranked_lists=[["a", "b"], ["b", "a"]])
        # a 和 b 都出现两次, 分数应相近
        assert scores["a"] > 0
        assert scores["b"] > 0

    def test_empty_lists(self):
        """空列表应返回空字典."""
        assert rrf_scores(ranked_lists=[]) == {}

    def test_empty_ranked_list(self):
        """包含空排序列表应不报错."""
        scores = rrf_scores(ranked_lists=[[], ["a"]])
        assert scores["a"] > 0

    def test_higher_rank_higher_score(self):
        """排名越靠前分数越高."""
        scores = rrf_scores(ranked_lists=[["x"]], k=60)
        expected = 1.0 / (60 + 0 + 1)
        assert abs(scores["x"] - expected) < 1e-9


# ---------------------------------------------------------------------------
# JSONL 持久化
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJsonlPersistence:
    """persist_docs_jsonl / load_docs_jsonl 往返测试."""

    def test_roundtrip(self, tmp_path: pathlib.Path):
        """写入后读回应保持一致."""
        docs = [
            Document(page_content="hello", metadata={"source": "a", "chunk_id": "1"}),
            Document(page_content="world", metadata={"source": "b"}),
        ]
        path = persist_docs_jsonl(docs, tmp_path / "out.jsonl")
        assert pathlib.Path(path).exists()

        loaded = load_docs_jsonl(tmp_path / "out.jsonl")
        assert len(loaded) == 2
        assert loaded[0].page_content == "hello"
        assert loaded[0].metadata["source"] == "a"
        assert loaded[1].page_content == "world"

    def test_load_missing_file_returns_empty(self, tmp_path: pathlib.Path):
        """文件不存在时返回空列表."""
        assert load_docs_jsonl(tmp_path / "nope.jsonl") == []

    def test_load_empty_lines_skipped(self, tmp_path: pathlib.Path):
        """空行应被跳过."""
        f = tmp_path / "empty_lines.jsonl"
        f.write_text("\n\n", encoding="utf-8")
        assert load_docs_jsonl(f) == []

    def test_persist_creates_parent_dir(self, tmp_path: pathlib.Path):
        """写入时应自动创建父目录."""
        deep = tmp_path / "a" / "b" / "c.jsonl"
        persist_docs_jsonl([], deep)
        assert deep.exists()

    def test_metadata_non_dict_normalized_to_empty(self, tmp_path: pathlib.Path):
        """metadata 非 dict 时应归一化为空字典."""
        f = tmp_path / "bad_meta.jsonl"
        f.write_text('{"page_content": "x", "metadata": "not a dict"}\n', encoding="utf-8")
        loaded = load_docs_jsonl(f)
        assert len(loaded) == 1
        assert loaded[0].metadata == {}
