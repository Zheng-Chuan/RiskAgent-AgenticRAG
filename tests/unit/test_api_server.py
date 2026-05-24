"""Unit tests for riskagent_agenticrag.api.server module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests: Health Check
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHealthEndpoint:
    """Test /healthz endpoint."""

    def test_healthz_returns_200(self, test_client):
        """GET /healthz should return 200 with status='ok'."""
        resp = test_client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Tests: LLM Usage
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLLMUsageEndpoint:
    """Test /v1/llm/usage endpoint."""

    @patch("riskagent_agenticrag.api.server.get_token_tracker")
    def test_llm_usage_returns_structure(self, mock_tracker_fn, test_client):
        """GET /v1/llm/usage should return usage data from tracker."""
        mock_tracker = MagicMock()
        mock_tracker.get_usage.return_value = {
            "total_prompt_tokens": 100,
            "total_completion_tokens": 50,
            "total_calls": 5,
            "hourly_tokens": 80,
            "daily_tokens": 150,
            "alert_status": {"hourly": False, "daily": False},
        }
        mock_tracker_fn.return_value = mock_tracker

        resp = test_client.get("/v1/llm/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_prompt_tokens" in data
        assert "total_completion_tokens" in data
        assert data["total_calls"] == 5


# ---------------------------------------------------------------------------
# Tests: /v1/ask with Mocked RAG
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAskEndpoint:
    """Test /v1/ask endpoint."""

    @patch("riskagent_agenticrag.api.server.system")
    def test_ask_returns_full_schema(self, mock_system, test_client):
        """/v1/ask with valid request should return full AskResponse schema."""
        mock_system.chat.return_value = {
            "status": "ok",
            "answer": "FRTB is a regulatory framework.",
            "citations": [{"source": "doc1.pdf", "page": 1}],
            "claims": [{"claim": "FRTB defines capital requirements"}],
            "evidence_set": [{"text": "context snippet"}],
            "decision_log": [{"step": "retrieve", "result": "found 4 docs"}],
            "failure_reason": None,
            "debug": {"run_id": "test-run-123", "model_id": "test-model"},
        }

        resp = test_client.post("/v1/ask", json={"question": "What is FRTB?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["answer"] == "FRTB is a regulatory framework."
        assert "request_id" in data
        assert isinstance(data["citations"], list)
        assert isinstance(data["claims"], list)
        assert isinstance(data["evidence_set"], list)
        assert isinstance(data["decision_log"], list)
        assert data["error"] is None

    def test_invalid_request_body_returns_422(self, test_client):
        """/v1/ask with empty question should return 422."""
        resp = test_client.post("/v1/ask", json={"question": ""})
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["error_code"] == "invalid_request"

    def test_missing_question_returns_422(self, test_client):
        """/v1/ask without required field should return 422."""
        resp = test_client.post("/v1/ask", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Auth Required
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAuthRequired:
    """Test authentication when enabled."""

    @patch("riskagent_agenticrag.api.server.system")
    def test_auth_required_when_enabled(self, mock_system):
        """When auth is enabled, missing key should return 401."""
        mock_system.chat.return_value = {"status": "ok", "answer": "test"}

        overrides = {
            "RISKAGENT_API_AUTH_ENABLED": "true",
            "API_KEY_SECRET": "test-secret-key-12345",
            "EMBEDDINGS_PROVIDER": "hash",
        }
        with patch.dict(os.environ, overrides):
            from fastapi.testclient import TestClient
            from riskagent_agenticrag.api.server import app
            client = TestClient(app)

            # No API key -> 401
            resp = client.post("/v1/ask", json={"question": "What is FRTB?"})
            assert resp.status_code == 401

    @patch("riskagent_agenticrag.api.server.system")
    def test_auth_passes_with_valid_key(self, mock_system):
        """When auth is enabled and correct key provided, request succeeds."""
        mock_system.chat.return_value = {
            "status": "ok", "answer": "test answer",
            "citations": [], "claims": [], "evidence_set": [],
            "decision_log": [], "failure_reason": None, "debug": {},
        }

        overrides = {
            "RISKAGENT_API_AUTH_ENABLED": "true",
            "API_KEY_SECRET": "test-secret-key-12345",
            "EMBEDDINGS_PROVIDER": "hash",
        }
        with patch.dict(os.environ, overrides):
            from fastapi.testclient import TestClient
            from riskagent_agenticrag.api.server import app
            client = TestClient(app)

            resp = client.post(
                "/v1/ask",
                json={"question": "What is FRTB?"},
                headers={"X-API-Key": "test-secret-key-12345"},
            )
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Readyz
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestReadyzEndpoint:
    """Test /readyz endpoint."""

    @patch("riskagent_agenticrag.api.server._ready_details")
    def test_readyz_returns_ready(self, mock_details, test_client):
        """When all checks pass, /readyz returns 200 with status='ready'."""
        mock_details.return_value = (True, {"index_manifest": {"ok": True}})

        resp = test_client.get("/readyz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    @patch("riskagent_agenticrag.api.server._ready_details")
    def test_readyz_returns_not_ready(self, mock_details, test_client):
        """When checks fail, /readyz returns 503 with status='not_ready'."""
        mock_details.return_value = (False, {"index_manifest": {"ok": False}})

        resp = test_client.get("/readyz")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
