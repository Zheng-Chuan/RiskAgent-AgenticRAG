"""retriever_factory 单元测试 -- 覆盖 _csv_env_list 与 build_retriever 构建逻辑."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from riskagent_agenticrag.rag.retriever_factory import _csv_env_list, build_retriever

# ---------------------------------------------------------------------------
# _csv_env_list
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCsvEnvList:
    """_csv_env_list 环境变量解析测试."""

    def test_empty_env_returns_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RISKAGENT_TEST_LIST", None)
            result = _csv_env_list("RISKAGENT_TEST_LIST", ["a", "b"])
            assert result == ["a", "b"]

    def test_single_value(self):
        with patch.dict(os.environ, {"RISKAGENT_TEST_LIST": "x"}):
            result = _csv_env_list("RISKAGENT_TEST_LIST", ["a"])
            assert result == ["x"]

    def test_multiple_values(self):
        with patch.dict(os.environ, {"RISKAGENT_TEST_LIST": "a,b,c"}):
            result = _csv_env_list("RISKAGENT_TEST_LIST", [])
            assert result == ["a", "b", "c"]

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"RISKAGENT_TEST_LIST": " a , b , c "}):
            result = _csv_env_list("RISKAGENT_TEST_LIST", [])
            assert result == ["a", "b", "c"]

    def test_deduplicates(self):
        with patch.dict(os.environ, {"RISKAGENT_TEST_LIST": "a,b,a"}):
            result = _csv_env_list("RISKAGENT_TEST_LIST", [])
            assert result == ["a", "b"]

    def test_skips_empty_entries(self):
        with patch.dict(os.environ, {"RISKAGENT_TEST_LIST": "a,,b,"}):
            result = _csv_env_list("RISKAGENT_TEST_LIST", [])
            assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# build_retriever
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildRetriever:
    """build_retriever 构建链路测试."""

    def test_build_retriever_returns_advanced_index_retriever(self, tmp_path: Path):
        """build_retriever 应返回 AdvancedIndexRetriever 实例."""
        with patch("riskagent_agenticrag.rag.retriever_factory.load_sparse_corpus", return_value=[]), \
             patch("riskagent_agenticrag.rag.retriever_factory.DenseMilvusRetriever") as mock_dense_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.HybridRetriever") as mock_hybrid_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.QueryIntelligentRetriever") as mock_qi_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.AdvancedIndexRetriever") as mock_adv_cls:
            mock_dense_cls.return_value = MagicMock()
            mock_hybrid_cls.return_value = MagicMock()
            mock_qi_cls.return_value = MagicMock()
            mock_adv_cls.return_value = MagicMock()

            retriever = build_retriever(persist_dir=tmp_path, final_k=4)

            mock_dense_cls.assert_called_once()
            mock_hybrid_cls.assert_called_once()
            mock_qi_cls.assert_called_once()
            mock_adv_cls.assert_called_once()
            assert retriever is mock_adv_cls.return_value

    def test_build_retriever_reads_env_overrides(self, tmp_path: Path):
        """build_retriever 应读取环境变量配置 dense_k / sparse_k 等."""
        env_overrides = {
            "RISKAGENT_DENSE_K": "15",
            "RISKAGENT_SPARSE_K": "20",
            "RISKAGENT_RERANKER_MODEL": "test/reranker",
        }
        with patch.dict(os.environ, env_overrides), \
             patch("riskagent_agenticrag.rag.retriever_factory.load_sparse_corpus", return_value=[]), \
             patch("riskagent_agenticrag.rag.retriever_factory.DenseMilvusRetriever") as mock_dense_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.HybridRetriever") as mock_hybrid_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.QueryIntelligentRetriever") as mock_qi_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.AdvancedIndexRetriever") as mock_adv_cls:
            mock_dense_cls.return_value = MagicMock()
            mock_hybrid_cls.return_value = MagicMock()
            mock_qi_cls.return_value = MagicMock()
            mock_adv_cls.return_value = MagicMock()

            build_retriever(persist_dir=tmp_path, final_k=4)

            # 验证 DenseMilvusRetrieverConfig k 使用了环境变量
            _, dense_kwargs = mock_dense_cls.call_args
            assert dense_kwargs["config"].k == 15

            # 验证 HybridConfig 读取了环境变量
            _, hybrid_kwargs = mock_hybrid_cls.call_args
            assert hybrid_kwargs["config"].dense_k == 15
            assert hybrid_kwargs["config"].sparse_k == 20
            assert hybrid_kwargs["config"].reranker_model == "test/reranker"

    def test_build_retriever_default_reranker_when_env_empty(self, tmp_path: Path):
        """RISKAGENT_RERANKER_MODEL 未设置时应使用默认 reranker."""
        env = {k: v for k, v in os.environ.items() if k != "RISKAGENT_RERANKER_MODEL"}
        with patch.dict(os.environ, env, clear=True), \
             patch("riskagent_agenticrag.rag.retriever_factory.load_sparse_corpus", return_value=[]), \
             patch("riskagent_agenticrag.rag.retriever_factory.DenseMilvusRetriever") as mock_dense_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.HybridRetriever") as mock_hybrid_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.QueryIntelligentRetriever") as mock_qi_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.AdvancedIndexRetriever") as mock_adv_cls:
            mock_dense_cls.return_value = MagicMock()
            mock_hybrid_cls.return_value = MagicMock()
            mock_qi_cls.return_value = MagicMock()
            mock_adv_cls.return_value = MagicMock()

            build_retriever(persist_dir=tmp_path, final_k=4)

            _, hybrid_kwargs = mock_hybrid_cls.call_args
            assert hybrid_kwargs["config"].reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def test_build_retriever_base_final_k_at_least_12(self, tmp_path: Path):
        """base_final_k 应至少为 max(12, final_k*3)."""
        with patch("riskagent_agenticrag.rag.retriever_factory.load_sparse_corpus", return_value=[]), \
             patch("riskagent_agenticrag.rag.retriever_factory.DenseMilvusRetriever") as mock_dense_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.HybridRetriever") as mock_hybrid_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.QueryIntelligentRetriever") as mock_qi_cls, \
             patch("riskagent_agenticrag.rag.retriever_factory.AdvancedIndexRetriever") as mock_adv_cls:
            mock_dense_cls.return_value = MagicMock()
            mock_hybrid_cls.return_value = MagicMock()
            mock_qi_cls.return_value = MagicMock()
            mock_adv_cls.return_value = MagicMock()

            build_retriever(persist_dir=tmp_path, final_k=2)

            _, hybrid_kwargs = mock_hybrid_cls.call_args
            assert hybrid_kwargs["config"].final_k >= 12
