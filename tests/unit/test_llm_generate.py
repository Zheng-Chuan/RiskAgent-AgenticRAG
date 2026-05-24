"""Unit tests for riskagent_agenticrag.llm.generate module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from riskagent_agenticrag.llm.governance import LLMGovernanceError
from riskagent_agenticrag.llm.llm_cache import CachedResponse, LLMCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_settings(base_url: str = "https://n1n.ai/v1"):
    """Create a mock settings object."""
    s = MagicMock()
    s.llm.resolved_api_key.get_secret_value.return_value = "sk-fake-key"
    s.llm.model = "test-model"
    s.llm.base_url = base_url
    s.llm_governance.max_retries = 3
    s.llm_governance.retry_backoff_base = 0.01
    s.llm_governance.timeout_total = 60
    s.llm_governance.cache_max_size = 100
    return s


def _mock_governor(allowed: bool = True):
    gov = MagicMock()
    if allowed:
        gov.allow.return_value = (True, {"priority": "default", "tokens_available": 10000.0})
    else:
        gov.allow.return_value = (False, {"reason": "rate_limited", "priority": "default", "retry_after_s": 5.0})
    return gov


# ---------------------------------------------------------------------------
# Tests: Route Selection
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRouteSelection:
    """Test that _call_llm_core selects the right backend based on URL."""

    @patch("riskagent_agenticrag.llm.generate.get_token_tracker")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cache")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    @patch("riskagent_agenticrag.llm.generate._call_via_curl")
    def test_n1n_ai_url_uses_curl(self, mock_curl, mock_settings_obj, mock_get_settings,
                                   mock_gov_fn, mock_cache_fn, mock_tracker_fn):
        """URL containing 'n1n.ai' should route to _call_via_curl."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_settings_obj.llm.model = "test-model"
        mock_settings_obj.llm.base_url = "https://api.n1n.ai/v1"
        mock_get_settings.return_value = _mock_settings()
        mock_gov_fn.return_value = _mock_governor(allowed=True)

        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        tracker = MagicMock()
        mock_tracker_fn.return_value = tracker

        mock_curl.return_value = ("response text", {"prompt_tokens": 10, "completion_tokens": 5})

        from riskagent_agenticrag.llm.generate import _call_llm_core
        result = _call_llm_core("test prompt")

        mock_curl.assert_called_once()
        assert result == "response text"

    @patch("riskagent_agenticrag.llm.generate.get_token_tracker")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cache")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    @patch("riskagent_agenticrag.llm.generate._call_via_langchain")
    def test_other_url_uses_langchain(self, mock_langchain, mock_settings_obj,
                                      mock_get_settings, mock_gov_fn, mock_cache_fn, mock_tracker_fn):
        """URL without 'n1n.ai' should route to _call_via_langchain."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_settings_obj.llm.model = "test-model"
        mock_settings_obj.llm.base_url = "https://api.openai.com/v1"
        mock_get_settings.return_value = _mock_settings(base_url="https://api.openai.com/v1")
        mock_gov_fn.return_value = _mock_governor(allowed=True)

        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        tracker = MagicMock()
        mock_tracker_fn.return_value = tracker

        mock_langchain.return_value = ("langchain response", {"prompt_tokens": 20, "completion_tokens": 10})

        from riskagent_agenticrag.llm.generate import _call_llm_core
        result = _call_llm_core("test prompt")

        mock_langchain.assert_called_once()
        assert result == "langchain response"


# ---------------------------------------------------------------------------
# Tests: Usage Parsing & Token Estimation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUsageParsing:
    """Test usage parsing and token estimation fallback."""

    @patch("riskagent_agenticrag.llm.generate.get_token_tracker")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cache")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    @patch("riskagent_agenticrag.llm.generate._call_via_langchain")
    def test_token_estimation_fallback(self, mock_langchain, mock_settings_obj,
                                       mock_get_settings, mock_gov_fn, mock_cache_fn, mock_tracker_fn):
        """When usage is zero, fallback estimation uses len // 4."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_settings_obj.llm.model = "test-model"
        mock_settings_obj.llm.base_url = "https://api.openai.com/v1"
        mock_get_settings.return_value = _mock_settings(base_url="https://api.openai.com/v1")
        mock_gov_fn.return_value = _mock_governor(allowed=True)

        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        tracker = MagicMock()
        mock_tracker_fn.return_value = tracker

        # Return zero usage to trigger fallback
        mock_langchain.return_value = ("a" * 100, {"prompt_tokens": 0, "completion_tokens": 0})

        from riskagent_agenticrag.llm.generate import _call_llm_core
        _call_llm_core("test prompt")

        # tracker.record should be called with estimated tokens (len // 4)
        tracker.record.assert_called_once()
        call_args = tracker.record.call_args
        # completion_tokens should be len("a" * 100) // 4 = 25
        assert call_args[0][2] == 25  # completion_tokens


# ---------------------------------------------------------------------------
# Tests: Retry on Transient Error
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRetryLogic:
    """Test retry on transient errors."""

    @patch("riskagent_agenticrag.llm.generate.time.sleep")
    @patch("riskagent_agenticrag.llm.generate.get_token_tracker")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cache")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    @patch("riskagent_agenticrag.llm.generate._call_via_langchain")
    def test_retry_on_transient_error(self, mock_langchain, mock_settings_obj,
                                      mock_get_settings, mock_gov_fn, mock_cache_fn,
                                      mock_tracker_fn, mock_sleep):
        """Transient error on first attempt should retry and succeed."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_settings_obj.llm.model = "test-model"
        mock_settings_obj.llm.base_url = "https://api.openai.com/v1"
        mock_get_settings.return_value = _mock_settings(base_url="https://api.openai.com/v1")
        mock_gov_fn.return_value = _mock_governor(allowed=True)

        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        tracker = MagicMock()
        mock_tracker_fn.return_value = tracker

        # First call raises a transient error, second succeeds
        mock_langchain.side_effect = [
            ConnectionError("connection reset"),
            ("success after retry", {"prompt_tokens": 10, "completion_tokens": 5}),
        ]

        from riskagent_agenticrag.llm.generate import _call_llm_core
        result = _call_llm_core("test prompt")

        assert result == "success after retry"
        assert mock_langchain.call_count == 2
        mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Governance Blocks
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGovernanceBlocking:
    """Test that governance denial raises LLMGovernanceError."""

    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    def test_governance_blocks_request(self, mock_settings_obj, mock_get_settings, mock_gov_fn):
        """When governance denies, LLMGovernanceError should be raised."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_get_settings.return_value = _mock_settings()
        mock_gov_fn.return_value = _mock_governor(allowed=False)

        from riskagent_agenticrag.llm.generate import _call_llm_core
        with pytest.raises(LLMGovernanceError):
            _call_llm_core("test prompt")


# ---------------------------------------------------------------------------
# Tests: Cache Hit
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCacheHit:
    """Test cache returns cached content on hit."""

    @patch("riskagent_agenticrag.llm.generate.get_token_tracker")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cache")
    @patch("riskagent_agenticrag.llm.generate.get_llm_cost_governor")
    @patch("riskagent_agenticrag.llm.generate.get_settings")
    @patch("riskagent_agenticrag.llm.generate.settings")
    def test_cache_returns_cached_content(self, mock_settings_obj, mock_get_settings,
                                          mock_gov_fn, mock_cache_fn, mock_tracker_fn):
        """When cache has a hit, return cached content without calling LLM."""
        mock_settings_obj.llm.resolved_api_key.get_secret_value.return_value = "sk-test"
        mock_settings_obj.llm.model = "test-model"
        mock_settings_obj.llm.base_url = "https://api.openai.com/v1"
        mock_get_settings.return_value = _mock_settings(base_url="https://api.openai.com/v1")
        mock_gov_fn.return_value = _mock_governor(allowed=True)

        cached_resp = CachedResponse(
            content="cached answer",
            prompt_tokens=10,
            completion_tokens=5,
            model="test-model",
            cached_at=time.time(),
        )
        cache = MagicMock()
        cache.get.return_value = cached_resp
        mock_cache_fn.return_value = cache

        tracker = MagicMock()
        mock_tracker_fn.return_value = tracker

        from riskagent_agenticrag.llm.generate import _call_llm_core
        result = _call_llm_core("test prompt")

        assert result == "cached answer"
        tracker.record.assert_called_once()
        # Verify cached=True in the record call
        call_kwargs = tracker.record.call_args
        assert call_kwargs[1]["cached"] is True
