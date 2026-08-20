"""LLM generate 模块补充测试.

覆盖 llm/generate.py 中的纯函数和 mock 子进程/langchain 路径:
_is_transient_error / _call_via_curl / _call_via_langchain / call_llm_json_with_model.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from riskagent_agenticrag.llm.generate import (
    _call_via_curl,
    _call_via_langchain,
    _is_transient_error,
    call_llm_json,
    call_llm_json_with_model,
    call_llm_text,
    call_llm_text_with_model,
    _parse_json_response,
)


# ---------------------------------------------------------------------------
# _is_transient_error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsTransientError:
    """瞬时错误判断测试."""

    def test_timeout_is_transient(self):
        assert _is_transient_error(subprocess.TimeoutExpired("cmd", 30)) is True

    def test_connection_error_is_transient(self):
        assert _is_transient_error(ConnectionError("refused")) is True

    def test_os_error_is_transient(self):
        assert _is_transient_error(OSError("boom")) is True

    def test_429_rate_limit_is_transient(self):
        assert _is_transient_error(RuntimeError("HTTP 429 rate limit exceeded")) is True

    def test_500_server_error_is_transient(self):
        assert _is_transient_error(RuntimeError("HTTP 500 internal server error")) is True

    def test_timeout_message_is_transient(self):
        assert _is_transient_error(RuntimeError("request timeout")) is True

    def test_connection_message_is_transient(self):
        assert _is_transient_error(RuntimeError("connection reset")) is True

    def test_non_transient_returns_false(self):
        assert _is_transient_error(ValueError("invalid input")) is False

    def test_plain_runtime_error_returns_false(self):
        assert _is_transient_error(RuntimeError("something else")) is False


# ---------------------------------------------------------------------------
# _call_via_curl (mock subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallViaCurl:
    """curl 子进程调用测试 (mock subprocess)."""

    def test_successful_call_returns_content_and_usage(self):
        """成功调用应返回 content 和 usage."""
        fake_response = {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = (__import__("json").dumps(fake_response)).encode()
        fake_result.stderr = b""

        with patch("subprocess.run", return_value=fake_result):
            content, usage = _call_via_curl(
                "https://api.test.com/chat/completions",
                "sk-test",
                {"model": "m", "messages": []},
                timeout=30,
            )
        assert content == "Hello world"
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5

    def test_curl_failure_raises_runtime_error(self):
        """curl 返回非零时应抛出 RuntimeError."""
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stdout = b""
        fake_result.stderr = b"curl: error"

        with patch("subprocess.run", return_value=fake_result):
            with pytest.raises(RuntimeError, match="curl failed"):
                _call_via_curl("https://api.test.com", "sk", {}, timeout=30)

    def test_api_error_in_body_raises(self):
        """响应体含 error 字段时应抛出 RuntimeError."""
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = b'{"error": {"message": "bad request", "type": "invalid_request"}}'
        fake_result.stderr = b""

        with patch("subprocess.run", return_value=fake_result):
            with pytest.raises(RuntimeError, match="API error"):
                _call_via_curl("https://api.test.com", "sk", {}, timeout=30)

    def test_empty_content_returns_empty_string(self):
        """content 为空时应返回空字符串."""
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = b'{"choices": [{"message": {"content": null}}], "usage": {}}'
        fake_result.stderr = b""

        with patch("subprocess.run", return_value=fake_result):
            content, usage = _call_via_curl("https://api.test.com", "sk", {}, timeout=30)
        assert content == ""
        assert usage["prompt_tokens"] == 0


# ---------------------------------------------------------------------------
# _call_via_langchain (mock ChatOpenAI)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallViaLangchain:
    """langchain ChatOpenAI 调用测试 (mock)."""

    def test_returns_content_and_usage(self):
        """应返回 content 和 usage."""
        fake_msg = MagicMock()
        fake_msg.content = "LLM response"
        fake_msg.response_metadata = {
            "token_usage": {"prompt_tokens": 15, "completion_tokens": 8}
        }

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value.invoke.return_value = fake_msg
            content, usage = _call_via_langchain(
                model="gpt-4", base_url="https://api.test.com",
                api_key="sk", temperature=0.0, max_tokens=None,
                timeout_total=30, prompt="hello",
            )
        assert content == "LLM response"
        assert usage["prompt_tokens"] == 15
        assert usage["completion_tokens"] == 8

    def test_headers_from_env(self):
        """应从环境变量构建 headers."""
        fake_msg = MagicMock()
        fake_msg.content = "resp"
        fake_msg.response_metadata = {}

        import os
        with patch.dict(os.environ, {"OPENROUTER_SITE_URL": "https://site.com", "OPENROUTER_APP_NAME": "MyApp"}), \
             patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value.invoke.return_value = fake_msg
            _call_via_langchain("m", "https://x", "k", 0.0, None, 30, "p")
            _, kwargs = mock_cls.call_args
            assert kwargs["default_headers"]["HTTP-Referer"] == "https://site.com"
            assert kwargs["default_headers"]["X-Title"] == "MyApp"

    def test_no_usage_metadata(self):
        """无 token_usage 时应返回零."""
        fake_msg = MagicMock()
        fake_msg.content = "resp"
        fake_msg.response_metadata = {}

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value.invoke.return_value = fake_msg
            content, usage = _call_via_langchain("m", "https://x", "k", 0.0, None, 30, "p")
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0

    def test_max_tokens_passed_when_set(self):
        """max_tokens 不为 None 时应传入."""
        fake_msg = MagicMock()
        fake_msg.content = "resp"
        fake_msg.response_metadata = {}

        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value.invoke.return_value = fake_msg
            _call_via_langchain("m", "https://x", "k", 0.0, 100, 30, "p")
            _, kwargs = mock_cls.call_args
            assert kwargs["max_tokens"] == 100


# ---------------------------------------------------------------------------
# try_parse_json_response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseJsonResponse:
    """JSON 响应容错解析测试."""

    def test_valid_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_code_block(self):
        """应去除 markdown 代码块包裹."""
        text = '```json\n{"sufficient": true}\n```'
        result = _parse_json_response(text)
        assert result == {"sufficient": True}

    def test_plain_code_block(self):
        """应去除普通代码块包裹."""
        text = '```\n{"query": "test"}\n```'
        result = _parse_json_response(text)
        assert result == {"query": "test"}

    def test_json_embedded_in_text(self):
        """应从文本中提取 JSON."""
        text = 'Here is the result:\n{"isrel": 0.8}\nDone.'
        result = _parse_json_response(text)
        assert result == {"isrel": 0.8}

    def test_empty_raises_runtime_error(self):
        """空文本应抛出 RuntimeError."""
        with pytest.raises(RuntimeError, match="LLM did not return valid JSON"):
            _parse_json_response("")

    def test_invalid_json_raises_runtime_error(self):
        """非 JSON 文本应抛出 RuntimeError."""
        with pytest.raises(RuntimeError, match="LLM did not return valid JSON"):
            _parse_json_response("not json at all")
