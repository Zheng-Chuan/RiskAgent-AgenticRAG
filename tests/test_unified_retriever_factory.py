from __future__ import annotations

import importlib
import pathlib
import sys
import types
import unittest
from unittest.mock import patch


class UnifiedRetrieverFactoryTest(unittest.TestCase):
    def test_build_retriever_wraps_hybrid_query_intel_and_advanced_index(self) -> None:
        persist_dir = pathlib.Path("/tmp/riskagent-test-persist")
        fake_dense_module = types.ModuleType("riskagent_agenticrag.rag.dense_milvus_retriever")
        fake_hybrid_module = types.ModuleType("riskagent_agenticrag.rag.hybrid_retriever")
        fake_query_module = types.ModuleType("riskagent_agenticrag.rag.query_intelligence")
        fake_advanced_module = types.ModuleType("riskagent_agenticrag.rag.advanced_index_retriever")
        fake_sparse_module = types.ModuleType("riskagent_agenticrag.rag.sparse_index")

        class _FakeDenseConfig:
            def __init__(self, k: int):
                self.k = k

        class _FakeDenseRetriever:
            def __init__(self, *args, **kwargs):
                pass

        fake_dense_module.DenseMilvusRetriever = _FakeDenseRetriever
        fake_dense_module.DenseMilvusRetrieverConfig = _FakeDenseConfig

        class _FakeHybridConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class _FakeQueryConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class _FakeAdvancedConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class _FakeHybridRetriever:
            def __init__(self, *args, **kwargs):
                pass

        class _FakeQueryRetriever:
            def __init__(self, *args, **kwargs):
                pass

        class _FakeAdvancedRetriever:
            def __init__(self, *args, **kwargs):
                pass

        fake_hybrid_module.HybridConfig = _FakeHybridConfig
        fake_hybrid_module.HybridRetriever = _FakeHybridRetriever
        fake_query_module.QueryIntelConfig = _FakeQueryConfig
        fake_query_module.QueryIntelligentRetriever = _FakeQueryRetriever
        fake_advanced_module.AdvancedIndexConfig = _FakeAdvancedConfig
        fake_advanced_module.AdvancedIndexRetriever = _FakeAdvancedRetriever
        fake_sparse_module.load_sparse_corpus = lambda persist_dir: []

        previous = sys.modules.get("riskagent_agenticrag.rag.dense_milvus_retriever")
        previous_hybrid = sys.modules.get("riskagent_agenticrag.rag.hybrid_retriever")
        previous_query = sys.modules.get("riskagent_agenticrag.rag.query_intelligence")
        previous_advanced = sys.modules.get("riskagent_agenticrag.rag.advanced_index_retriever")
        previous_sparse = sys.modules.get("riskagent_agenticrag.rag.sparse_index")
        sys.modules["riskagent_agenticrag.rag.dense_milvus_retriever"] = fake_dense_module
        sys.modules["riskagent_agenticrag.rag.hybrid_retriever"] = fake_hybrid_module
        sys.modules["riskagent_agenticrag.rag.query_intelligence"] = fake_query_module
        sys.modules["riskagent_agenticrag.rag.advanced_index_retriever"] = fake_advanced_module
        sys.modules["riskagent_agenticrag.rag.sparse_index"] = fake_sparse_module
        retriever_factory = importlib.import_module("riskagent_agenticrag.rag.retriever_factory")

        try:
            with patch("riskagent_agenticrag.rag.retriever_factory.load_sparse_corpus", return_value=[]), patch(
                "riskagent_agenticrag.rag.retriever_factory.DenseMilvusRetriever",
                return_value="dense",
            ) as dense_cls, patch(
                "riskagent_agenticrag.rag.retriever_factory.HybridRetriever",
                return_value="hybrid",
            ) as hybrid_cls, patch(
                "riskagent_agenticrag.rag.retriever_factory.QueryIntelligentRetriever",
                return_value="query_intel",
            ) as qi_cls, patch(
                "riskagent_agenticrag.rag.retriever_factory.AdvancedIndexRetriever",
                return_value="advanced",
            ) as adv_cls:
                out = retriever_factory.build_retriever(persist_dir=persist_dir, final_k=4)

            self.assertEqual(out, "advanced")
            dense_cls.assert_called_once()
            hybrid_cls.assert_called_once()
            qi_cls.assert_called_once()
            adv_cls.assert_called_once()

            hybrid_kwargs = hybrid_cls.call_args.kwargs
            self.assertEqual(hybrid_kwargs["dense_retriever"], "dense")
            self.assertEqual(hybrid_kwargs["config"].final_k, 12)

            qi_kwargs = qi_cls.call_args.kwargs
            self.assertEqual(qi_kwargs["base_retriever"], "hybrid")
            self.assertEqual(qi_kwargs["config"].final_k, 12)

            adv_kwargs = adv_cls.call_args.kwargs
            self.assertEqual(adv_kwargs["base_retriever"], "query_intel")
            self.assertEqual(adv_kwargs["persist_dir"], persist_dir)
            self.assertEqual(adv_kwargs["config"].final_k, 4)
        finally:
            if previous is None:
                sys.modules.pop("riskagent_agenticrag.rag.dense_milvus_retriever", None)
            else:
                sys.modules["riskagent_agenticrag.rag.dense_milvus_retriever"] = previous
            if previous_hybrid is None:
                sys.modules.pop("riskagent_agenticrag.rag.hybrid_retriever", None)
            else:
                sys.modules["riskagent_agenticrag.rag.hybrid_retriever"] = previous_hybrid
            if previous_query is None:
                sys.modules.pop("riskagent_agenticrag.rag.query_intelligence", None)
            else:
                sys.modules["riskagent_agenticrag.rag.query_intelligence"] = previous_query
            if previous_advanced is None:
                sys.modules.pop("riskagent_agenticrag.rag.advanced_index_retriever", None)
            else:
                sys.modules["riskagent_agenticrag.rag.advanced_index_retriever"] = previous_advanced
            if previous_sparse is None:
                sys.modules.pop("riskagent_agenticrag.rag.sparse_index", None)
            else:
                sys.modules["riskagent_agenticrag.rag.sparse_index"] = previous_sparse


if __name__ == "__main__":
    unittest.main()
