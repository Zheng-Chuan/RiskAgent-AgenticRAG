from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


def _inject_fake_st_module(cross_encoder) -> None:
    """向 sys.modules 注入假 sentence_transformers 模块.

    容器/CI 不安装 sentence_transformers (可选依赖), 直接 patch 其属性会
    ModuleNotFoundError; 注入假模块让延迟导入拿到 mock 的 CrossEncoder.
    """
    mod = types.ModuleType("sentence_transformers")
    mod.CrossEncoder = cross_encoder  # type: ignore[attr-defined]
    sys.modules["sentence_transformers"] = mod


@pytest.fixture(autouse=True)
def _local_reranker_only(monkeypatch):
    """禁用远程 reranker fallback, 保证单测不打真实 API."""
    monkeypatch.setenv("RISKAGENT_RERANKER_PROVIDER", "local")


@pytest.mark.unit
def test_hybrid_retriever_falls_back_to_second_reranker_candidate():
    from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever

    long_text = "Basel market risk capital rule " * 20
    dense = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content=long_text,
                    metadata={"chunk_id": "c1", "source": "a.md", "section_path": "sec/a"},
                )
            ]
        )
    )
    fake_reranker = MagicMock(predict=MagicMock(return_value=[0.9]))

    # 模拟 CrossEncoder 延迟导入: bad/model 抛 OSError, good/model 返回 fake_reranker
    def _fake_cross_encoder(model_name: str, **_kwargs):
        if "bad" in str(model_name):
            raise OSError("missing model")
        return fake_reranker

    _inject_fake_st_module(_fake_cross_encoder)
    retriever = HybridRetriever(
        dense_retriever=dense,
        sparse_docs=[],
        config=HybridConfig(
            dense_k=4,
            sparse_k=4,
            candidate_k=4,
            rerank_k=4,
            final_k=2,
            reranker_model="bad/model",
            reranker_candidates=("bad/model", "good/model"),
        ),
    )
    docs = retriever.invoke("Basel market risk capital")

    assert len(docs) == 1
    assert docs[0].metadata["reranker_model"] == "good/model"
    debug = retriever.debug_stats()
    assert debug["active_reranker_model"] == "good/model"
    assert debug["reranker_status"] == "fallback_enabled"
    assert debug["reranker_init_errors"] == ["bad/model: OSError"]


@pytest.mark.unit
def test_hybrid_retriever_reports_unavailable_when_all_candidates_fail():
    from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever

    long_text = "Basel market risk capital rule " * 20
    dense = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content=long_text,
                    metadata={"chunk_id": "c1", "source": "a.md", "section_path": "sec/a"},
                )
            ]
        )
    )

    # 所有候选模型都失败, reranker 应报告 unavailable
    _inject_fake_st_module(lambda *a, **k: (_ for _ in ()).throw(OSError("missing model")))
    retriever = HybridRetriever(
        dense_retriever=dense,
        sparse_docs=[],
        config=HybridConfig(
            dense_k=4,
            sparse_k=4,
            candidate_k=4,
            rerank_k=4,
            final_k=2,
            reranker_model="bad/model",
            reranker_candidates=("bad/model", "bad/second"),
        ),
    )
    docs = retriever.invoke("Basel market risk capital")

    assert len(docs) == 1
    assert "rerank_score" not in (docs[0].metadata or {})
    debug = retriever.debug_stats()
    assert debug["active_reranker_model"] == ""
    assert debug["reranker_status"] == "unavailable"
    assert debug["reranker_init_errors"] == [
        "bad/model: OSError",
        "bad/second: OSError",
    ]


@pytest.mark.unit
def test_hybrid_retriever_skips_reranker_when_no_candidates_survive_filter():
    from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever

    dense = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="too short",
                    metadata={"chunk_id": "c1", "source": "a.md", "section_path": "sec/a"},
                )
            ]
        )
    )
    fake_reranker = MagicMock(predict=MagicMock(return_value=[]))

    # reranker 初始化成功, 但 chunk 太短被过滤掉, 不应调用 reranker.predict
    _inject_fake_st_module(lambda *a, **k: fake_reranker)
    retriever = HybridRetriever(
        dense_retriever=dense,
        sparse_docs=[],
        config=HybridConfig(
            dense_k=4,
            sparse_k=4,
            candidate_k=4,
            rerank_k=4,
            final_k=2,
            reranker_model="good/model",
            reranker_candidates=("good/model",),
            min_chunk_chars=80,
        ),
    )
    docs = retriever.invoke("Basel market risk capital")

    assert docs == []
    fake_reranker.predict.assert_not_called()


# ---------------------------------------------------------------------------
# 辅助函数测试
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveHfModelPath:
    """_resolve_hf_model_path 模型路径解析测试."""

    def test_returns_original_when_snapshots_missing(self, tmp_path):
        from riskagent_agenticrag.rag.hybrid_retriever import _resolve_hf_model_path

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = _resolve_hf_model_path("test/model")
            assert result == "test/model"

    def test_returns_original_when_no_snapshot_dirs(self, tmp_path):
        from riskagent_agenticrag.rag.hybrid_retriever import _resolve_hf_model_path

        # 创建 snapshots 目录但无子目录
        snapshots_dir = tmp_path / ".cache" / "huggingface" / "hub" / "models--test--model" / "snapshots"
        snapshots_dir.mkdir(parents=True)
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = _resolve_hf_model_path("test/model")
            assert result == "test/model"

    def test_returns_latest_snapshot_dir(self, tmp_path):
        import time
        from riskagent_agenticrag.rag.hybrid_retriever import _resolve_hf_model_path

        snapshots_dir = tmp_path / ".cache" / "huggingface" / "hub" / "models--test--model" / "snapshots"
        old_dir = snapshots_dir / "old"
        new_dir = snapshots_dir / "new"
        old_dir.mkdir(parents=True)
        new_dir.mkdir(parents=True)
        # 设置不同的修改时间
        import os
        old_time = time.time() - 100
        new_time = time.time()
        os.utime(old_dir, (old_time, old_time))
        os.utime(new_dir, (new_time, new_time))

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = _resolve_hf_model_path("test/model")
            assert result.endswith("new")


@pytest.mark.unit
class TestMergeUniqueStrings:
    """_merge_unique_strings 去重测试."""

    def test_deduplicates(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_unique_strings
        assert _merge_unique_strings(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_strips_whitespace(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_unique_strings
        assert _merge_unique_strings([" a ", "b", " a "]) == ["a", "b"]

    def test_skips_empty(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_unique_strings
        assert _merge_unique_strings(["", "a", None, "b"]) == ["a", "b"]


@pytest.mark.unit
class TestCandidateModels:
    """_candidate_models 候选模型列表测试."""

    def test_inserts_primary_first(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _candidate_models
        result = _candidate_models(primary="primary", candidates=["c1", "c2"])
        assert result[0] == "primary"
        assert "c1" in result
        assert "c2" in result

    def test_deduplicates(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _candidate_models
        result = _candidate_models(primary="p", candidates=["p", "c1"])
        assert result == ["p", "c1"]

    def test_empty_primary(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _candidate_models
        result = _candidate_models(primary="", candidates=["c1", "c2"])
        assert result == ["c1", "c2"]


@pytest.mark.unit
class TestMergeSources:
    """_merge_sources 检索来源标记测试."""

    def test_appends_source(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_sources
        doc = Document(page_content="x", metadata={})
        _merge_sources(doc, "dense")
        assert doc.metadata["retrieval_sources"] == ["dense"]

    def test_does_not_duplicate(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_sources
        doc = Document(page_content="x", metadata={"retrieval_sources": ["dense"]})
        _merge_sources(doc, "dense")
        assert doc.metadata["retrieval_sources"] == ["dense"]

    def test_initializes_when_not_list(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _merge_sources
        doc = Document(page_content="x", metadata={"retrieval_sources": "not a list"})
        _merge_sources(doc, "dense")
        assert doc.metadata["retrieval_sources"] == ["dense"]


@pytest.mark.unit
class TestComputeMetadataBoost:
    """_compute_metadata_boost 元数据加权测试."""

    def test_empty_query_tokens_returns_zero(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _compute_metadata_boost
        assert _compute_metadata_boost({}, set()) == 0.0

    def test_source_match_adds_boost(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _compute_metadata_boost
        boost = _compute_metadata_boost({"source": "frtb_doc.md"}, {"frtb"})
        assert boost > 0.0

    def test_section_match_adds_boost(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _compute_metadata_boost
        boost = _compute_metadata_boost({"section_path": "risk/capital"}, {"risk"})
        assert boost > 0.0

    def test_no_match_returns_zero(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _compute_metadata_boost
        boost = _compute_metadata_boost({"source": "doc.md", "section_path": "sec"}, {"nonexistent"})
        assert boost == 0.0

    def test_boost_capped_at_0_15(self):
        from riskagent_agenticrag.rag.hybrid_retriever import _compute_metadata_boost
        # 多个匹配应被封顶在 0.15
        boost = _compute_metadata_boost(
            {"source": "a b c d e", "section_path": "a b c"},
            {"a", "b", "c", "d", "e"},
        )
        assert boost <= 0.15


@pytest.mark.unit
class TestPassesFilter:
    """_passes_filter chunk 质量过滤测试."""

    def _make_retriever(self, min_chars=80):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever
        dense = MagicMock(invoke=MagicMock(return_value=[]))
        return HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(min_chunk_chars=min_chars),
        )

    def test_short_text_filtered(self):
        retriever = self._make_retriever(min_chars=100)
        doc = Document(page_content="short", metadata={})
        assert retriever._passes_filter(doc) is False

    def test_table_of_contents_filtered(self):
        retriever = self._make_retriever(min_chars=10)
        doc = Document(page_content="table of contents chapter 1 2 3 4 5 6 7 8 9 0", metadata={})
        assert retriever._passes_filter(doc) is False

    def test_business_portal_wikipedia_filtered(self):
        retriever = self._make_retriever(min_chars=10)
        doc = Document(page_content="business portal wikipedia article content 1 2 3 4 5", metadata={})
        assert retriever._passes_filter(doc) is False

    def test_low_alnum_filtered(self):
        retriever = self._make_retriever(min_chars=10)
        doc = Document(page_content="!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()", metadata={})
        assert retriever._passes_filter(doc) is False

    def test_valid_text_passes(self):
        retriever = self._make_retriever(min_chars=10)
        doc = Document(page_content="This is valid content with alphanumeric chars 12345", metadata={})
        assert retriever._passes_filter(doc) is True


@pytest.mark.unit
class TestDiversitySelect:
    """_diversity_select MMR 多样性选择测试."""

    def _make_retriever(self, final_k=3, max_per_source=2, max_per_section=1):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever
        dense = MagicMock(invoke=MagicMock(return_value=[]))
        return HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(final_k=final_k, max_per_source=max_per_source, max_per_section=max_per_section),
        )

    def test_limits_per_source(self):
        retriever = self._make_retriever(final_k=2, max_per_source=1)
        docs = [
            Document(page_content="a", metadata={"source": "s1"}),
            Document(page_content="b", metadata={"source": "s1"}),
            Document(page_content="c", metadata={"source": "s2"}),
        ]
        result = retriever._diversity_select(docs)
        sources = [d.metadata["source"] for d in result]
        assert sources.count("s1") == 1
        assert "s2" in sources

    def test_limits_per_section(self):
        retriever = self._make_retriever(final_k=2, max_per_section=1)
        docs = [
            Document(page_content="a", metadata={"section_path": "sec1"}),
            Document(page_content="b", metadata={"section_path": "sec1"}),
            Document(page_content="c", metadata={"section_path": "sec2"}),
        ]
        result = retriever._diversity_select(docs)
        sections = [d.metadata["section_path"] for d in result]
        assert sections.count("sec1") == 1
        assert "sec2" in sections

    def test_returns_at_most_final_k(self):
        retriever = self._make_retriever(final_k=2)
        docs = [
            Document(page_content="a", metadata={"source": "s1"}),
            Document(page_content="b", metadata={"source": "s2"}),
            Document(page_content="c", metadata={"source": "s3"}),
        ]
        result = retriever._diversity_select(docs)
        assert len(result) == 2

    def test_fills_remaining_when_not_enough(self):
        retriever = self._make_retriever(final_k=5, max_per_source=1)
        docs = [
            Document(page_content="a", metadata={"source": "s1"}),
            Document(page_content="b", metadata={"source": "s1"}),
            Document(page_content="c", metadata={"source": "s1"}),
        ]
        result = retriever._diversity_select(docs)
        assert len(result) == 3


@pytest.mark.unit
class TestCoarseScore:
    """_coarse_score 粗排分数测试."""

    def test_combines_rrf_bm25_boost(self):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever
        dense = MagicMock(invoke=MagicMock(return_value=[]))
        retriever = HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(),
        )
        doc = Document(page_content="x", metadata={"rrf_score": 0.5, "bm25_score": 0.4, "metadata_boost": 0.1})
        score = retriever._coarse_score(doc)
        assert abs(score - (0.5 + 0.5 * 0.4 + 0.1)) < 1e-9


@pytest.mark.unit
class TestSetConfidenceGap:
    """_set_confidence_gap 置信度差值测试."""

    def test_sets_gap_for_all_docs(self):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridRetriever
        docs = [
            Document(page_content="a", metadata={"rerank_score": 0.9}),
            Document(page_content="b", metadata={"rerank_score": 0.7}),
        ]
        HybridRetriever._set_confidence_gap(docs, "rerank_score")
        assert docs[0].metadata["confidence_gap_to_top1"] == 0.0
        assert abs(docs[1].metadata["confidence_gap_to_top1"] - 0.2) < 1e-9

    def test_empty_docs_noop(self):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridRetriever
        HybridRetriever._set_confidence_gap([], "rerank_score")


@pytest.mark.unit
class TestSparseQuery:
    """_sparse_query 查询去重测试."""

    def test_deduplicates_tokens(self):
        from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever
        dense = MagicMock(invoke=MagicMock(return_value=[]))
        retriever = HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(),
        )
        result = retriever._sparse_query("hello world hello foo bar world")
        tokens = result.split()
        # 不应有重复
        assert len(tokens) == len(set(tokens))
