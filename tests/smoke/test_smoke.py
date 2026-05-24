"""
Smoke tests - quick validation that all components can initialize.
Run: make test-smoke
No Docker or LLM connection required.
"""
from __future__ import annotations

import os

import pytest

# Ensure hash embeddings are used (no model download needed)
os.environ.setdefault("EMBEDDINGS_PROVIDER", "hash")


@pytest.mark.smoke
class TestModuleImports:
    """Verify all source modules can be imported without errors."""

    def test_import_config(self):
        from riskagent_agenticrag.config import settings  # noqa: F401

    def test_import_llm_modules(self):
        from riskagent_agenticrag.llm import generate, governance, token_tracker, llm_cache  # noqa: F401

    def test_import_rag_modules(self):
        from riskagent_agenticrag.rag import (  # noqa: F401
            agentic_primitives,
            source_loader,
            ingestion,
            chunking,
            embeddings,
            query_intelligence,
            self_rag,
            utils,
        )

    def test_import_rag_retrieval_modules(self):
        from riskagent_agenticrag.rag import (  # noqa: F401
            hybrid_retriever,
            dense_milvus_retriever,
            sparse_index,
            advanced_index,
            advanced_index_retriever,
            retriever_factory,
            pipeline,
        )

    def test_import_orchestration(self):
        from riskagent_agenticrag.orchestration import (  # noqa: F401
            langgraph_runner,
            nodes,
            state,
            trace,
        )

    def test_import_api(self):
        from riskagent_agenticrag.api import server, schemas  # noqa: F401

    def test_import_validators(self):
        from riskagent_agenticrag.validators import gates  # noqa: F401

    def test_import_artifacts(self):
        from riskagent_agenticrag.artifacts import storage  # noqa: F401

    def test_import_exceptions(self):
        from riskagent_agenticrag import exceptions, constants  # noqa: F401

    def test_import_contracts(self):
        from riskagent_agenticrag.contracts import structured  # noqa: F401

    def test_import_indexing(self):
        from riskagent_agenticrag.indexing import indexer, milvus_store  # noqa: F401

    def test_import_evaluation(self):
        from riskagent_agenticrag.evaluation import (  # noqa: F401
            ragas_metrics,
            advanced_metrics,
            report_generator,
            citation_precision,
            domain_consistency,
        )

    def test_import_agents(self):
        from riskagent_agenticrag.agents import data_agent  # noqa: F401

    def test_import_cache(self):
        from riskagent_agenticrag import cache  # noqa: F401

    def test_import_app(self):
        from riskagent_agenticrag import app  # noqa: F401


@pytest.mark.smoke
class TestComponentInit:
    """Verify key components can be instantiated."""

    def test_settings_load(self):
        from riskagent_agenticrag.config.settings import get_settings

        s = get_settings()
        assert s.llm.model is not None
        assert s.llm.base_url is not None

    def test_governance_init(self):
        from riskagent_agenticrag.llm.governance import LLMCostGovernor

        gov = LLMCostGovernor()
        assert gov is not None

    def test_token_tracker_init(self):
        from riskagent_agenticrag.llm.token_tracker import TokenTracker

        tracker = TokenTracker()
        assert tracker is not None

    def test_llm_cache_init(self):
        from riskagent_agenticrag.llm.llm_cache import LLMCache

        cache = LLMCache(max_size=10)
        assert cache.size() == 0

    def test_llm_cache_put_get(self):
        from riskagent_agenticrag.llm.llm_cache import CachedResponse, LLMCache

        cache = LLMCache(max_size=5)
        key = cache.make_key(
            messages=[{"role": "user", "content": "hello"}],
            model="test",
            temperature=0.0,
            max_tokens=100,
        )
        assert isinstance(key, str)
        assert len(key) == 64  # SHA-256 hex digest
        assert cache.get(key) is None  # miss

    def test_schema_ask_request(self):
        from riskagent_agenticrag.api.schemas import AskRequest

        req = AskRequest(question="test question")
        assert req.question == "test question"

    def test_schema_health_response(self):
        from riskagent_agenticrag.api.schemas import HealthResponse

        resp = HealthResponse(status="ok")
        assert resp.status == "ok"

    def test_app_server_creation(self):
        from riskagent_agenticrag.api.server import app

        assert app is not None
        routes = [r.path for r in app.routes]
        assert "/healthz" in routes
        assert "/v1/ask" in routes

    def test_exceptions_hierarchy(self):
        from riskagent_agenticrag.exceptions import (
            RiskAgentError,
            LLMError,
            LLMAPIError,
            ConfigurationError,
        )

        assert issubclass(LLMError, RiskAgentError)
        assert issubclass(LLMAPIError, LLMError)
        assert issubclass(ConfigurationError, RiskAgentError)

    def test_constants_values(self):
        from riskagent_agenticrag.constants import (
            DEFAULT_CHUNK_SIZE,
            DEFAULT_EMBEDDING_DIMENSION,
            DEFAULT_RETRIEVAL_K,
        )

        assert DEFAULT_CHUNK_SIZE > 0
        assert DEFAULT_EMBEDDING_DIMENSION > 0
        assert DEFAULT_RETRIEVAL_K > 0

    def test_token_bucket(self):
        from riskagent_agenticrag.llm.governance import TokenBucket

        bucket = TokenBucket(capacity=100.0, refill_per_second=10.0)
        assert bucket.capacity == 100.0
        assert bucket.available > 0
        assert bucket.consume(50.0) is True
        assert bucket.consume(200.0) is False

    def test_contracts_structured(self):
        from riskagent_agenticrag.contracts.structured import FailureCategory, RunStatus

        # Type alias checks
        assert "no_evidence" in FailureCategory.__args__
        assert "ok" in RunStatus.__args__
