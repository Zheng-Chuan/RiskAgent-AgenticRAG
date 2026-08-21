"""Trace 模块测试.

覆盖 orchestration/trace.py: _ensure_trace / _trace_node_start / _trace_node_end /
_doc_trace_row / _trace_retrieval_diag / _normalize_snippet.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document
from riskagent_agenticrag.orchestration.trace import (
    _doc_trace_row,
    _ensure_trace,
    _normalize_snippet,
    _trace_node_end,
    _trace_node_start,
    _trace_retrieval_diag,
)

# ---------------------------------------------------------------------------
# _ensure_trace
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnsureTrace:
    """trace 初始化测试."""

    def test_creates_trace_when_missing(self):
        """无 trace 时应创建."""
        state = {}
        trace = _ensure_trace(state)
        assert "trace" in state
        assert trace["events"] == []
        assert trace["nodes"] == []

    def test_fixes_non_dict_trace(self):
        """trace 非 dict 时应重建."""
        state = {"trace": "invalid"}
        trace = _ensure_trace(state)
        assert isinstance(trace, dict)
        assert trace["events"] == []
        assert trace["nodes"] == []

    def test_fixes_non_list_events(self):
        """events 非 list 时应重建."""
        state = {"trace": {"events": "not a list", "nodes": []}}
        trace = _ensure_trace(state)
        assert trace["events"] == []

    def test_fixes_non_list_nodes(self):
        """nodes 非 list 时应重建."""
        state = {"trace": {"events": [], "nodes": "not a list"}}
        trace = _ensure_trace(state)
        assert trace["nodes"] == []

    def test_preserves_valid_trace(self):
        """有效 trace 应保持不变."""
        state = {"trace": {"events": [1], "nodes": [2]}}
        trace = _ensure_trace(state)
        assert trace["events"] == [1]
        assert trace["nodes"] == [2]


# ---------------------------------------------------------------------------
# _trace_node_start / _trace_node_end
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTraceNodeLifecycle:
    """节点追踪 start/end 测试."""

    def test_start_appends_node_entry(self):
        """start 应追加节点条目."""
        state = {}
        start_ms = _trace_node_start(state, "retrieve", {"query": "FRTB"})
        assert start_ms > 0
        trace = state["trace"]
        assert len(trace["nodes"]) == 1
        assert trace["nodes"][0]["name"] == "retrieve"
        assert trace["nodes"][0]["payload"]["query"] == "FRTB"

    def test_end_adds_latency_and_result(self):
        """end 应补充 latency_ms 和 result."""
        state = {}
        start_ms = _trace_node_start(state, "grade", {"input": 1})
        _trace_node_end(state, "grade", start_ms, {"result": "sufficient"})
        node = state["trace"]["nodes"][0]
        assert "end_ms" in node
        assert "latency_ms" in node
        assert node["result"]["result"] == "sufficient"

    def test_end_with_token_usage(self):
        """end 带 token_usage 时应写入."""
        state = {}
        start_ms = _trace_node_start(state, "generate", {})
        _trace_node_end(state, "generate", start_ms, {}, token_usage={"prompt_tokens": 10})
        node = state["trace"]["nodes"][0]
        assert node["token_usage"]["prompt_tokens"] == 10

    def test_end_without_matching_node_noop(self):
        """无匹配节点时 end 不报错."""
        state = {}
        _trace_node_end(state, "nonexistent", 0.0, {})


# ---------------------------------------------------------------------------
# _normalize_snippet / _doc_trace_row
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocTraceRow:
    """文档 trace 行构建测试."""

    def test_normalize_snippet(self):
        """应压缩空白."""
        assert _normalize_snippet("  hello   world  ") == "hello world"
        assert _normalize_snippet(None) == ""
        assert _normalize_snippet("") == ""

    def test_basic_doc_with_metadata(self):
        """应提取 chunk_id / source / snippet 等字段."""
        doc = Document(
            page_content="delta risk content",
            metadata={"chunk_id": "c1", "source": "doc.md", "section_path": "Risk/Delta", "page": 1},
        )
        row = _doc_trace_row(doc, snippet_chars=100)
        assert row["chunk_id"] == "c1"
        assert row["source"] == "doc.md"
        assert row["section_path"] == "Risk/Delta"
        assert row["page"] == 1
        assert "delta" in row["snippet"]

    def test_expanded_text_preferred_for_snippet(self):
        """有 expanded_text 时 snippet 应优先使用它."""
        doc = Document(
            page_content="original",
            metadata={"chunk_id": "c", "expanded_text": "expanded version text"},
        )
        row = _doc_trace_row(doc, snippet_chars=50)
        assert "expanded" in row["snippet"]

    def test_non_dict_metadata_handled(self):
        """非 dict metadata 应安全处理."""
        doc = MagicMock()
        doc.metadata = "not a dict"
        doc.page_content = "content"
        row = _doc_trace_row(doc, snippet_chars=50)
        assert row["chunk_id"] == ""
        assert row["source"] == ""

    def test_snippet_truncated(self):
        """snippet 应截断到指定长度."""
        doc = Document(page_content="x" * 500, metadata={"chunk_id": "c"})
        row = _doc_trace_row(doc, snippet_chars=50)
        assert len(row["snippet"]) <= 50


# ---------------------------------------------------------------------------
# _trace_retrieval_diag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTraceRetrievalDiag:
    """检索诊断埋点测试."""

    def test_extracts_dense_sparse_rerank_mmr_config(self):
        """应提取 dense / sparse / rerank / mmr / config 诊断."""
        state = {}
        debug_stats = {
            "dense_count": 30, "dense_latency_ms": 50.0, "dense_top1_score": 0.9,
            "sparse_count": 20, "sparse_latency_ms": 30.0,
            "rerank_input_count": 50, "rerank_output_count": 10, "rerank_latency_ms": 100.0,
            "mmr_before_count": 10, "mmr_after_count": 8,
            "dense_k": 30, "sparse_k": 20, "candidate_k": 50, "rerank_k": 10,
            "final_k": 4, "rrf_k": 60, "reranker_model": "ce", "has_bm25": True,
        }
        _trace_retrieval_diag(state, debug_stats)
        diag = state["trace"]["retrieval_diag"]
        assert diag["dense"]["count"] == 30
        assert diag["dense"]["top1_score"] == 0.9
        assert diag["sparse"]["count"] == 20
        assert diag["rerank"]["input_count"] == 50
        assert diag["rerank"]["output_count"] == 10
        assert diag["mmr"]["before_count"] == 10
        assert diag["config"]["dense_k"] == 30
        assert diag["config"]["has_bm25"] is True

    def test_fallback_on_exception(self):
        """异常时应回退到 fallback 字段."""
        state = {}
        bad_stats = MagicMock()
        bad_stats.get.side_effect = RuntimeError("boom")
        _trace_retrieval_diag(state, bad_stats)
        diag = state["trace"]["retrieval_diag"]
        assert "fallback" in diag

    def test_empty_stats_handled(self):
        """空 stats 应正常处理."""
        state = {}
        _trace_retrieval_diag(state, {})
        diag = state["trace"]["retrieval_diag"]
        assert "dense" in diag
        assert diag["dense"]["count"] == 0
