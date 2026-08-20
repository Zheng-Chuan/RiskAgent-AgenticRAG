"""App 模块补充测试.

覆盖 app.py 的 _merge_history / get_status / chat (无索引) / _ensure_resources.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from riskagent_agenticrag.app import RiskAgentSystem


# ---------------------------------------------------------------------------
# _merge_history
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMergeHistory:
    """对话历史合并测试."""

    def test_no_history_returns_question(self):
        """无 history 时直接返回 question."""
        sys = RiskAgentSystem.__new__(RiskAgentSystem)
        assert sys._merge_history(question="What is FRTB?", history=None) == "What is FRTB?"

    def test_empty_history_returns_question(self):
        """空 history 时返回 question."""
        sys = RiskAgentSystem.__new__(RiskAgentSystem)
        assert sys._merge_history(question="q", history=[]) == "q"

    def test_history_merged(self):
        """有 history 时应合并到 question 前."""
        sys = RiskAgentSystem.__new__(RiskAgentSystem)
        result = sys._merge_history(question="q3", history=[("q1", "a1"), ("q2", "a2")])
        assert "Conversation so far" in result
        assert "q1" in result
        assert "a1" in result
        assert "q3" in result

    def test_history_limited_to_last_three(self):
        """只保留最近 3 轮."""
        sys = RiskAgentSystem.__new__(RiskAgentSystem)
        history = [(f"q{i}", f"a{i}") for i in range(5)]
        result = sys._merge_history(question="final", history=history)
        assert "q4" in result
        assert "q3" in result
        assert "q2" in result
        assert "q1" not in result

    def test_empty_pairs_skipped(self):
        """空 user/assistant 对应被跳过."""
        sys = RiskAgentSystem.__new__(RiskAgentSystem)
        result = sys._merge_history(question="q", history=[("", "")])
        assert result == "q"


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetStatus:
    """系统状态描述测试."""

    def test_status_contains_provider_and_model(self):
        """状态应包含 provider 和 model."""
        with patch("riskagent_agenticrag.app.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.model = "deepseek-v3"
            mock_settings.project_name = "test"
            sys = RiskAgentSystem.__new__(RiskAgentSystem)
            status = sys.get_status()
        assert "openai" in status
        assert "deepseek-v3" in status

    def test_status_with_no_model_uses_default(self):
        """无 model 时应使用 default."""
        with patch("riskagent_agenticrag.app.settings") as mock_settings:
            mock_settings.llm.provider = "hf"
            mock_settings.llm.model = None
            mock_settings.project_name = "test"
            sys = RiskAgentSystem.__new__(RiskAgentSystem)
            status = sys.get_status()
        assert "default" in status


# ---------------------------------------------------------------------------
# chat (无索引)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChatNoIndex:
    """chat 方法在无索引时的行为测试."""

    def test_chat_returns_error_when_no_index(self):
        """无索引时应返回错误状态."""
        with patch("riskagent_agenticrag.app.settings") as mock_settings, \
             patch("riskagent_agenticrag.app.setup_langsmith"):
            mock_settings.llm.provider = "openai"
            mock_settings.llm.model = "m"
            mock_settings.project_name = "test"
            mock_settings.paths.milvus_lite_dir.exists.return_value = False
            mock_settings.paths.milvus_lite_dir.__truediv__ = MagicMock()
            sys = RiskAgentSystem.__new__(RiskAgentSystem)
            sys._retriever = None
            result = sys.chat(question="What is FRTB?")
        assert result["status"] == "error"
        assert "Index not found" in result.get("message", "")
