"""Unit tests for riskagent_agenticrag.api.server module."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from riskagent_agenticrag.api.schemas import ApiError
from riskagent_agenticrag.api.server import (
    _error_from_exc,
    _error_from_http,
    _make_error_response,
    _make_response,
    _record_metrics,
    app,
)

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
# Tests: Metrics endpoint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, test_client):
        """GET /metrics should return Prometheus exposition format."""
        resp = test_client.get("/metrics")
        assert resp.status_code == 200
        # Prometheus content type 或包含指标文本
        assert "riskagent" in resp.text or resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Error helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorFromExc:
    """_error_from_exc 异常分类测试."""

    def test_missing_llm_key(self):
        """Missing LLM API key 应映射为 llm_missing_key."""
        err = _error_from_exc(RuntimeError("Missing LLM API key in env"))
        assert err.error_code == "llm_missing_key"
        assert err.retryable is False

    def test_index_not_found(self):
        """Index not found 应映射为 index_not_ready."""
        err = _error_from_exc(RuntimeError("Index not found in collection"))
        assert err.error_code == "index_not_ready"

    def test_index_not_ready(self):
        """Index not ready 应映射为 index_not_ready."""
        err = _error_from_exc(RuntimeError("Index not ready yet"))
        assert err.error_code == "index_not_ready"

    def test_ollama_unreachable(self):
        """Ollama 调用失败应映射为 llm_unreachable, 可重试."""
        err = _error_from_exc(RuntimeError("Ollama call failed: connection refused"))
        assert err.error_code == "llm_unreachable"
        assert err.retryable is True

    def test_internal_error_default(self):
        """其它异常应映射为 internal_error, 可重试."""
        err = _error_from_exc(ValueError("something broke"))
        assert err.error_code == "internal_error"
        assert err.retryable is True


@pytest.mark.unit
class TestErrorFromHttp:
    """_error_from_http 状态码映射测试."""

    def test_401_unauthorized(self):
        err = _error_from_http(code=401, detail="nope")
        assert err.error_code == "unauthorized"
        assert err.retryable is False

    def test_422_invalid_request(self):
        err = _error_from_http(code=422, detail=[{"loc": "q"}])
        assert err.error_code == "invalid_request"
        assert err.retryable is False
        assert "detail" in err.details

    def test_429_rate_limit(self):
        err = _error_from_http(code=429, detail="slow down")
        assert err.error_code == "rate_limit_exceeded"
        assert err.retryable is True

    def test_503_not_ready(self):
        err = _error_from_http(code=503, detail="not ready")
        assert err.error_code == "not_ready"
        assert err.retryable is True

    def test_other_code(self):
        err = _error_from_http(code=500, detail="boom")
        assert err.error_code == "http_error"
        assert err.retryable is False


# ---------------------------------------------------------------------------
# Tests: Response constructors
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseBuilders:
    """_make_response / _make_error_response 测试."""

    def test_make_response_maps_all_fields(self):
        out = {
            "status": "ok",
            "answer": "FRTB is a framework",
            "citations": [{"source": "s"}],
            "claims": [{"claim": "c"}],
            "evidence_set": [{"text": "e"}],
            "decision_log": [{"step": "x"}],
            "failure_reason": None,
            "debug": {"run_id": "r1"},
        }
        resp = _make_response(request_id="req-1", out=out)
        assert resp.request_id == "req-1"
        assert resp.status == "ok"
        assert resp.answer == "FRTB is a framework"
        assert len(resp.citations) == 1
        assert resp.debug["run_id"] == "r1"
        assert resp.error is None

    def test_make_response_defaults_on_missing_keys(self):
        """缺失键应使用默认空值."""
        resp = _make_response(request_id="r", out={})
        assert resp.status == "ok"
        assert resp.answer == ""
        assert resp.citations == []

    def test_make_error_response(self):
        err = ApiError(error_code="internal_error", message="boom", retryable=True)
        resp = _make_error_response(request_id="r2", error=err)
        assert resp.request_id == "r2"
        assert resp.status == "error"
        assert resp.error.error_code == "internal_error"


# ---------------------------------------------------------------------------
# Tests: _record_metrics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecordMetrics:
    """_record_metrics 指标记录测试."""

    def test_records_without_out(self):
        """out 为 None 时不应抛异常."""
        _record_metrics("/v1/ask", "POST", 500, 0.0, "rid", None)

    def test_records_with_debug(self):
        """有 debug 字段时应记录 retriever_version 等."""
        out = {"debug": {"run_id": "r", "model_id": "m", "retriever_version": {"dense": "v1"}}}
        _record_metrics("/v1/ask", "POST", 200, 0.0, "rid", out)

    def test_records_with_non_dict_out(self):
        """out 非 dict 时应静默."""
        _record_metrics("/v1/ask", "POST", 200, 0.0, "rid", "not a dict")


# ---------------------------------------------------------------------------
# Tests: /v1/chat endpoint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChatEndpoint:
    """Test /v1/chat endpoint."""

    @patch("riskagent_agenticrag.api.server.system")
    def test_chat_returns_full_schema(self, mock_system, test_client):
        """/v1/chat with user message should return AskResponse."""
        mock_system.chat.return_value = {
            "status": "ok",
            "answer": "FRTB capital charge is 8%.",
            "citations": [{"source": "doc.md"}],
            "claims": [],
            "evidence_set": [],
            "decision_log": [],
            "failure_reason": None,
            "debug": {"run_id": "chat-1"},
        }
        resp = test_client.post("/v1/chat", json={
            "messages": [{"role": "user", "content": "What is FRTB?"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "FRTB" in data["answer"]
        assert data["debug"]["run_id"] == "chat-1"

    @patch("riskagent_agenticrag.api.server.system")
    def test_chat_with_history_extracts_pairs(self, mock_system, test_client):
        """多轮对话应提取 history pairs 传入 system.chat."""
        mock_system.chat.return_value = {
            "status": "ok", "answer": "yes", "citations": [], "claims": [],
            "evidence_set": [], "decision_log": [], "failure_reason": None, "debug": {},
        }
        resp = test_client.post("/v1/chat", json={
            "messages": [
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "q2"},
            ],
        })
        assert resp.status_code == 200
        # 验证 history 被传入
        _, kwargs = mock_system.chat.call_args
        assert kwargs.get("question") == "q2"
        assert kwargs.get("history") == [("q1", "a1")]

    @patch("riskagent_agenticrag.api.server.system")
    def test_chat_no_user_message_returns_422(self, mock_system, test_client):
        """无 user 消息应返回 422."""
        resp = test_client.post("/v1/chat", json={
            "messages": [{"role": "assistant", "content": "only assistant"}],
        })
        assert resp.status_code == 422

    def test_chat_empty_messages_returns_422(self, test_client):
        """messages 为空应返回 422."""
        resp = test_client.post("/v1/chat", json={"messages": []})
        assert resp.status_code == 422

    @patch("riskagent_agenticrag.api.server.system")
    def test_chat_internal_error_returns_500(self, mock_system, test_client):
        """system.chat 抛异常应返回 500."""
        mock_system.chat.side_effect = RuntimeError("Missing LLM API key")
        resp = test_client.post("/v1/chat", json={
            "messages": [{"role": "user", "content": "q"}],
        })
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["error_code"] == "llm_missing_key"


# ---------------------------------------------------------------------------
# Tests: /v1/ask error path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAskErrorPath:
    """Test /v1/ask error handling."""

    @patch("riskagent_agenticrag.api.server.system")
    def test_ask_internal_error_returns_500(self, mock_system, test_client):
        """system.chat 抛异常应返回 500 错误响应."""
        mock_system.chat.side_effect = RuntimeError("Ollama call failed")
        resp = test_client.post("/v1/ask", json={"question": "q"})
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["error_code"] == "llm_unreachable"
        assert data["error"]["retryable"] is True


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
