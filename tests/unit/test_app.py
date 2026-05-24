"""Unit tests for riskagent_agenticrag.app module (RiskAgentSystem)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests: Instantiation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRiskAgentSystemInit:
    """Test RiskAgentSystem instantiation with mocked dependencies."""

    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_can_instantiate_with_mocked_deps(self, mock_settings, mock_langsmith):
        """RiskAgentSystem should be instantiable without real deps."""
        mock_settings.project_name = "test-project"

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()

        assert system._retriever is None
        assert system._retriever_persist_dir is None
        mock_langsmith.assert_called_once_with(project_name="test-project")

    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_get_status(self, mock_settings, mock_langsmith):
        """get_status should return provider and model info."""
        mock_settings.project_name = "test"
        mock_settings.llm.provider = "openai"
        mock_settings.llm.model = "gpt-4o"

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()
        status = system.get_status()

        assert "openai" in status
        assert "gpt-4o" in status
        assert "LangGraph" in status


# ---------------------------------------------------------------------------
# Tests: chat() Delegation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestChatDelegation:
    """Test that chat() delegates to langgraph runner."""

    @patch("riskagent_agenticrag.app.extract_citations")
    @patch("riskagent_agenticrag.app.run_langgraph_agentic_chat")
    @patch("riskagent_agenticrag.app.build_retriever")
    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_chat_delegates_to_langgraph(self, mock_settings, mock_langsmith,
                                         mock_build_retriever, mock_runner,
                                         mock_citations):
        """chat() should call run_langgraph_agentic_chat with correct args."""
        mock_settings.project_name = "test"
        mock_persist_dir = MagicMock(spec=Path)
        mock_persist_dir.exists.return_value = True
        mock_persist_dir.__truediv__ = lambda self, other: MagicMock(exists=lambda: True)
        mock_settings.paths.milvus_lite_dir = mock_persist_dir

        mock_retriever = MagicMock()
        mock_build_retriever.return_value = mock_retriever

        mock_runner.return_value = {
            "status": "ok",
            "answer": "Test answer",
            "docs": [MagicMock()],
        }
        mock_citations.return_value = [{"source": "test.pdf"}]

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()
        result = system.chat(question="What is FRTB?", max_rounds=2, request_id="req-1")

        mock_runner.assert_called_once()
        call_kwargs = mock_runner.call_args[1]
        assert call_kwargs["question"] == "What is FRTB?"
        assert call_kwargs["retriever"] == mock_retriever
        assert call_kwargs["max_rounds"] == 2
        assert call_kwargs["request_id"] == "req-1"
        assert result["runner"] == "langgraph"
        assert "docs" not in result  # docs should be removed

    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_chat_returns_error_when_index_missing(self, mock_settings, mock_langsmith):
        """chat() should return error dict when index is not found."""
        mock_settings.project_name = "test"
        mock_persist_dir = MagicMock(spec=Path)
        mock_persist_dir.exists.return_value = False
        mock_settings.paths.milvus_lite_dir = mock_persist_dir

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()
        result = system.chat(question="test")

        assert result["status"] == "error"
        assert "Index not found" in result["message"]


# ---------------------------------------------------------------------------
# Tests: Error Handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestErrorHandling:
    """Test error handling when components fail."""

    @patch("riskagent_agenticrag.app.run_langgraph_agentic_chat")
    @patch("riskagent_agenticrag.app.build_retriever")
    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_chat_propagates_runner_exception(self, mock_settings, mock_langsmith,
                                              mock_build_retriever, mock_runner):
        """When langgraph runner raises, chat() should propagate the exception."""
        mock_settings.project_name = "test"
        mock_persist_dir = MagicMock(spec=Path)
        mock_persist_dir.exists.return_value = True
        mock_persist_dir.__truediv__ = lambda self, other: MagicMock(exists=lambda: True)
        mock_settings.paths.milvus_lite_dir = mock_persist_dir

        mock_build_retriever.return_value = MagicMock()
        mock_runner.side_effect = RuntimeError("LLM service unavailable")

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()

        with pytest.raises(RuntimeError, match="LLM service unavailable"):
            system.chat(question="test")

    @patch("riskagent_agenticrag.app.build_retriever")
    @patch("riskagent_agenticrag.app.setup_langsmith")
    @patch("riskagent_agenticrag.app.settings")
    def test_chat_propagates_retriever_build_error(self, mock_settings, mock_langsmith,
                                                    mock_build_retriever):
        """When build_retriever raises, chat() should propagate."""
        mock_settings.project_name = "test"
        mock_persist_dir = MagicMock(spec=Path)
        mock_persist_dir.exists.return_value = True
        mock_persist_dir.__truediv__ = lambda self, other: MagicMock(exists=lambda: True)
        mock_settings.paths.milvus_lite_dir = mock_persist_dir

        mock_build_retriever.side_effect = ValueError("Invalid persist dir")

        from riskagent_agenticrag.app import RiskAgentSystem
        system = RiskAgentSystem()

        with pytest.raises(ValueError, match="Invalid persist dir"):
            system.chat(question="test")
