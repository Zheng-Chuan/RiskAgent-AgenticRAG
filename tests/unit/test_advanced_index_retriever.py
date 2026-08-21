from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_default_route_does_not_expand_without_parent_signal(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import (
        AdvancedIndexConfig,
        AdvancedIndexRetriever,
    )

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="parent context " * 200, metadata={"parent_id": "p1", "parent_type": "section"})
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="desk requirements " * 30,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "default",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.05,
                    },
                )
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    docs = retriever.invoke("FRTB desk requirements")

    assert len(docs) == 1
    meta = docs[0].metadata or {}
    assert meta["expand_parent_route"] == "default"
    assert meta["expand_parent_applied"] is False
    assert "expanded_text" not in meta
    assert "parent_expand" not in (meta.get("indexing_sources") or [])


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_default_route_expands_when_parent_signal_is_strong(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import (
        AdvancedIndexConfig,
        AdvancedIndexRetriever,
    )

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="parent context " * 200, metadata={"parent_id": "p1", "parent_type": "section"})
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="desk requirements " * 20,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "default",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.05,
                    },
                )
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    with patch.object(retriever, "_parent_score_map", side_effect=[{"p1": 0.9}, {}]):
        docs = retriever.invoke("FRTB desk requirements")

    meta = docs[0].metadata or {}
    assert meta["expand_parent_route"] == "default"
    assert meta["expand_parent_applied"] is True
    assert meta["expand_parent_reason"] == "default_signal"
    assert meta["expanded_text"]
    assert "parent_expand" in (meta.get("indexing_sources") or [])


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_compare_route_expands_multiple_top_docs(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import (
        AdvancedIndexConfig,
        AdvancedIndexRetriever,
    )

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="compare parent one " * 120, metadata={"parent_id": "p1", "parent_type": "section"}),
        "p2": Document(page_content="compare parent two " * 120, metadata={"parent_id": "p2", "parent_type": "section"}),
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="first compare chunk " * 20,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "compare",
                        "coarse_score": 0.9,
                        "confidence_gap_to_top1": 0.0,
                    },
                ),
                Document(
                    page_content="second compare chunk " * 20,
                    metadata={
                        "parent_id": "p2",
                        "chunk_id": "c2",
                        "source": "b.md",
                        "query_route": "compare",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.25,
                    },
                ),
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    docs = retriever.invoke("Compare FRTB and Basel II.5")

    assert len(docs) == 2
    for doc in docs:
        meta = doc.metadata or {}
        assert meta["expand_parent_route"] == "compare"
        assert meta["expand_parent_applied"] is True
        assert meta["expand_parent_reason"] == "near_top"
        assert meta["expanded_text"]


# ---------------------------------------------------------------------------
# 辅助函数测试
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalize:
    """_normalize 分数归一化测试."""

    def test_empty_idxs_returns_empty(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _normalize
        assert _normalize([1.0, 2.0], []) == {}

    def test_normalizes_by_max(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _normalize
        # scores=[1.0, 2.0, 4.0], idxs=[0,2], max=4.0
        result = _normalize([1.0, 2.0, 4.0], [0, 2])
        assert abs(result[0] - 0.25) < 1e-9
        assert abs(result[2] - 1.0) < 1e-9

    def test_all_zero_scores_returns_zero(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _normalize
        result = _normalize([0.0, 0.0], [0, 1])
        assert result[0] == 0.0
        assert result[1] == 0.0


@pytest.mark.unit
class TestBestBaseScore:
    """_best_base_score 基础分数提取测试."""

    def test_rerank_score_priority(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _best_base_score
        d = Document(page_content="x", metadata={"rerank_score": 0.9, "coarse_score": 0.3, "rrf_score": 0.5})
        assert _best_base_score(d) == 0.9

    def test_coarse_when_no_rerank(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _best_base_score
        d = Document(page_content="x", metadata={"coarse_score": 0.3, "rrf_score": 0.5})
        # 优先级: rerank_score > coarse_score > rrf_score
        assert _best_base_score(d) == 0.3

    def test_zero_when_no_scores(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _best_base_score
        d = Document(page_content="x", metadata={})
        assert _best_base_score(d) == 0.0

    def test_empty_metadata(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import _best_base_score
        d = Document(page_content="x")
        assert _best_base_score(d) == 0.0


@pytest.mark.unit
class TestQueryRoute:
    """_query_route 查询路由测试."""

    def test_numeric_query_returns_numeric(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        # numeric 查询 (含数字和比较词)
        result = AdvancedIndexRetriever._query_route(
            query="desk exposure 500 million",
            docs=[Document(page_content="x", metadata={})],
        )
        assert result == "numeric"

    def test_doc_query_route_takes_priority(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        # doc metadata 中的 query_route 优先
        result = AdvancedIndexRetriever._query_route(
            query="some query",
            docs=[Document(page_content="x", metadata={"query_route": "compare"})],
        )
        assert result == "compare"

    def test_falls_back_to_route_name(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        # 无 numeric / 无 doc route, 回退到 _route_name
        result = AdvancedIndexRetriever._query_route(
            query="compare frtb and basel",
            docs=[Document(page_content="x", metadata={})],
        )
        # "compare" 是一个路由关键词
        assert result in ("compare", "default")


@pytest.mark.unit
class TestExpandPolicy:
    """_expand_policy 路由策略测试."""

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_compare_policy(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        retriever = AdvancedIndexRetriever(
            base_retriever=MagicMock(),
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=4),
        )
        result = retriever._expand_policy(route="compare")
        assert result.route == "compare"
        assert result.max_docs <= 3

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_numeric_policy(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        retriever = AdvancedIndexRetriever(
            base_retriever=MagicMock(),
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=4, max_expand_chars=2000),
        )
        result = retriever._expand_policy(route="numeric")
        assert result.route == "numeric"
        assert result.max_docs == 1

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_unknown_route_returns_default(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        retriever = AdvancedIndexRetriever(
            base_retriever=MagicMock(),
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=4),
        )
        result = retriever._expand_policy(route="nonexistent")
        assert result.route == "default"


@pytest.mark.unit
class TestExpandReason:
    """_expand_reason 展开理由测试."""

    def _make_policy(self, **kwargs):
        from riskagent_agenticrag.rag.advanced_index_retriever import ParentExpandPolicy
        defaults = dict(
            route="default", max_docs=1, max_chars=900,
            min_parent_signal=0.20, max_gap_to_top1=0.15, short_chunk_chars=260,
        )
        defaults.update(kwargs)
        return ParentExpandPolicy(**defaults)

    def test_rank_exceeds_max_docs_returns_empty(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        policy = self._make_policy(max_docs=2)
        result = AdvancedIndexRetriever._expand_reason(
            route="default", rank_idx=5, chunk_len=100,
            parent_signal=0.5, gap_to_top1=0.0, policy=policy,
        )
        assert result == ""

    def test_compare_parent_signal(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        policy = self._make_policy(route="compare", min_parent_signal=0.0)
        result = AdvancedIndexRetriever._expand_reason(
            route="compare", rank_idx=0, chunk_len=100,
            parent_signal=0.5, gap_to_top1=0.0, policy=policy,
        )
        assert result == "parent_signal"

    def test_numeric_requires_all_conditions(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        policy = self._make_policy(route="numeric", min_parent_signal=0.30, max_gap_to_top1=0.12, short_chunk_chars=260)
        # 不满足 short_chunk 条件
        result = AdvancedIndexRetriever._expand_reason(
            route="numeric", rank_idx=0, chunk_len=500,
            parent_signal=0.5, gap_to_top1=0.05, policy=policy,
        )
        assert result == ""
        # 满足全部条件
        result = AdvancedIndexRetriever._expand_reason(
            route="numeric", rank_idx=0, chunk_len=100,
            parent_signal=0.5, gap_to_top1=0.05, policy=policy,
        )
        assert result == "numeric_backing"

    def test_default_near_top_and_short_chunk(self):
        from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexRetriever
        policy = self._make_policy(route="default", min_parent_signal=0.30, max_gap_to_top1=0.15, short_chunk_chars=260)
        # 无 strong_signal, near_top, short_chunk
        result = AdvancedIndexRetriever._expand_reason(
            route="default", rank_idx=0, chunk_len=100,
            parent_signal=0.0, gap_to_top1=0.05, policy=policy,
        )
        assert result == "default_short_chunk"


@pytest.mark.unit
class TestDebugStats:
    """debug_stats 诊断统计测试."""

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_debug_stats_returns_all_fields(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock()
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(),
        )
        stats = retriever.debug_stats()
        assert "parents" in stats
        assert "summaries" in stats
        assert "hydes" in stats
        assert "expand_policies" in stats
        assert "compare" in stats["expand_policies"]
        assert "numeric" in stats["expand_policies"]

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_debug_stats_includes_base_debug(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock()
        base.debug_stats.return_value = {"dense_count": 10}
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(),
        )
        stats = retriever.debug_stats()
        assert stats["base_debug"]["dense_count"] == 10

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_debug_stats_handles_base_exception(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock()
        base.debug_stats.side_effect = RuntimeError("fail")
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(),
        )
        stats = retriever.debug_stats()
        assert stats["base_debug"] == {}


@pytest.mark.unit
class TestInvokeEdgeCases:
    """invoke 方法边界条件测试."""

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_invoke_empty_base_returns_empty(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock(invoke=MagicMock(return_value=[]))
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=4),
        )
        docs = retriever.invoke("query")
        assert docs == []

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_invoke_strips_empty_query(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock(invoke=MagicMock(return_value=[]))
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=4),
        )
        docs = retriever.invoke("   ")
        # 空白 query strip 后为空, base.invoke 返回空
        assert docs == []

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_invoke_limits_to_final_k(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base_docs = [
            Document(page_content=f"doc {i} " * 20, metadata={"coarse_score": 0.5, "chunk_id": f"c{i}"})
            for i in range(10)
        ]
        base = MagicMock(invoke=MagicMock(return_value=base_docs))
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(final_k=3),
        )
        docs = retriever.invoke("FRTB query")
        assert len(docs) == 3


@pytest.mark.unit
class TestParentScoreMap:
    """_parent_score_map 父文档分数映射测试."""

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_empty_bm25_returns_empty(self, _a, _b, _c):
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        base = MagicMock()
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(),
        )
        result = retriever._parent_score_map(bm25=None, docs=[], query="q", k=5)
        assert result == {}

    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
    @patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id", return_value={})
    def test_empty_query_tokens_returns_empty(self, _a, _b, _c):
        from rank_bm25 import BM25Okapi
        from riskagent_agenticrag.rag.advanced_index_retriever import (
            AdvancedIndexConfig,
            AdvancedIndexRetriever,
        )

        summary_docs = [Document(page_content="text", metadata={"parent_id": "p1"})]
        base = MagicMock()
        retriever = AdvancedIndexRetriever(
            base_retriever=base,
            persist_dir="/tmp/unused",
            config=AdvancedIndexConfig(),
        )
        retriever._summary_bm25 = BM25Okapi([["text"]])
        retriever._summary_docs = summary_docs
        result = retriever._parent_score_map(bm25=retriever._summary_bm25, docs=summary_docs, query="", k=5)
        assert result == {}
