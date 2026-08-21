"""Agentic RAG runner 单元测试 (RFC-004 阶段一)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

# ===========================================================================
# _build_system_prompt
# ===========================================================================

@pytest.mark.unit
def test_build_system_prompt_returns_non_empty():
    """_build_system_prompt 应返回非空字符串, 包含工具说明."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _build_system_prompt

    prompt = _build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 50
    assert "semantic_search" in prompt
    assert "keyword_search" in prompt


# ===========================================================================
# _execute_tool
# ===========================================================================

@pytest.mark.unit
def test_execute_tool_dispatches_correctly():
    """_execute_tool 应按名称分发到正确的工具."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _execute_tool

    mock_tool = MagicMock()
    mock_tool.name = "semantic_search"
    mock_tool.invoke = MagicMock(return_value=[{"text": "result"}])

    result = _execute_tool({"name": "semantic_search", "args": {"query": "test"}}, [mock_tool])
    assert result == [{"text": "result"}]
    mock_tool.invoke.assert_called_once_with({"query": "test"})


@pytest.mark.unit
def test_execute_tool_raises_on_unknown():
    """_execute_tool 对未知工具名应抛 ValueError."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _execute_tool

    mock_tool = MagicMock()
    mock_tool.name = "known_tool"

    with pytest.raises(ValueError, match="Unknown tool"):
        _execute_tool({"name": "unknown_tool", "args": {}}, [mock_tool])


# ===========================================================================
# _result_to_docs
# ===========================================================================

@pytest.mark.unit
def test_result_to_docs_converts_list():
    """_result_to_docs 应将 list[dict] 转为 Document 列表."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _result_to_docs

    result = [
        {"text": "doc1", "chunk_id": "c1", "source": "a.pdf", "score": 0.9},
        {"text": "doc2", "chunk_id": "c2", "source": "b.pdf"},
    ]
    docs = _result_to_docs(result)
    assert len(docs) == 2
    assert docs[0].page_content == "doc1"
    assert docs[0].metadata["chunk_id"] == "c1"
    assert docs[0].metadata["agentic_score"] == 0.9
    assert docs[1].page_content == "doc2"


@pytest.mark.unit
def test_result_to_docs_non_list_returns_empty():
    """非 list 输入应返回空列表."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _result_to_docs

    assert _result_to_docs({"text": "not a list"}) == []
    assert _result_to_docs("string") == []
    assert _result_to_docs(None) == []


@pytest.mark.unit
def test_result_to_docs_skips_non_dict_items():
    """list 中的非 dict 项应被跳过."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _result_to_docs

    result = [{"text": "valid", "chunk_id": "c1"}, "not_dict", 42]
    docs = _result_to_docs(result)
    assert len(docs) == 1
    assert docs[0].page_content == "valid"


# ===========================================================================
# _extract_token_usage
# ===========================================================================

@pytest.mark.unit
def test_extract_token_usage_from_response():
    """_extract_token_usage 应从 response_metadata 提取 token usage."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _extract_token_usage

    response = MagicMock()
    response.response_metadata = {
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 50}
    }
    usage = _extract_token_usage(response)
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50


@pytest.mark.unit
def test_extract_token_usage_defaults_to_zero():
    """无 token_usage 时应返回 0."""
    from riskagent_agenticrag.agents.agentic_rag_runner import _extract_token_usage

    response = MagicMock()
    response.response_metadata = {}
    usage = _extract_token_usage(response)
    assert usage["prompt_tokens"] == 0
    assert usage["completion_tokens"] == 0


# ===========================================================================
# run_agentic_rag: 完整流程 (mock LLM)
# ===========================================================================

@pytest.mark.unit
@patch("riskagent_agenticrag.agents.agentic_rag_runner._build_llm")
@patch("riskagent_agenticrag.agents.agentic_rag_runner.extract_citations", return_value=[{"source": "a.pdf"}])
@patch("riskagent_agenticrag.agents.agentic_rag_runner.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.agents.agentic_rag_runner.build_claims_from_answer", return_value=[])
def test_run_agentic_rag_returns_expected_keys(
    mock_claims, mock_evidence, mock_citations, mock_build_llm
):
    """run_agentic_rag 应返回包含所有必需字段的 dict."""
    from riskagent_agenticrag.agents.agentic_rag_runner import run_agentic_rag

    # mock LLM: 第一次 invoke 返回有 tool_calls, 第二次返回最终答案
    tool_response = MagicMock()
    tool_response.tool_calls = [{"name": "semantic_search", "args": {"query": "FRTB"}, "id": "tc1"}]
    tool_response.content = "searching..."
    tool_response.response_metadata = {}

    final_response = MagicMock()
    final_response.tool_calls = []
    final_response.content = "FRTB is a framework"
    final_response.response_metadata = {}

    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(side_effect=[tool_response, final_response])
    mock_build_llm.return_value = mock_llm

    # mock retriever 和工具结果
    retriever = MagicMock()
    # semantic_search 内部通过 contextvar 获取 retriever
    with patch("riskagent_agenticrag.agents.retrieval_tools._retriever_ctx") as mock_ctx:
        mock_ctx.get.return_value = retriever
        mock_ctx.set = MagicMock()
        # semantic_search 调用 retriever._base._base._dense.invoke
        dense = MagicMock()
        dense.invoke = MagicMock(return_value=[
            Document(page_content="FRTB content", metadata={"chunk_id": "c1", "dense_score": 0.9})
        ])
        hybrid = MagicMock()
        hybrid._dense = dense
        query_intel = MagicMock()
        query_intel._base = hybrid
        retriever._base = query_intel

        result = run_agentic_rag(question="What is FRTB?", retriever=retriever, max_tool_calls=2)

    assert "request_id" in result
    assert "answer" in result
    assert "docs" in result
    assert "citations" in result
    assert "claims" in result
    assert "evidence_set" in result
    assert "decision_log" in result
    assert "status" in result
    assert "failure_reason" in result
    assert "debug" in result
    assert "total_token_usage" in result
    assert result["answer"] == "FRTB is a framework"
    assert result["status"] == "ok"
    assert result["debug"]["runner"] == "agentic"


@pytest.mark.unit
@patch("riskagent_agenticrag.agents.agentic_rag_runner._build_llm")
@patch("riskagent_agenticrag.agents.agentic_rag_runner.extract_citations", return_value=[])
@patch("riskagent_agenticrag.agents.agentic_rag_runner.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.agents.agentic_rag_runner.build_claims_from_answer", return_value=[])
def test_run_agentic_rag_handles_llm_failure(
    mock_claims, mock_evidence, mock_citations, mock_build_llm
):
    """run_agentic_rag 在 LLM invoke 失败时应记录 failure_reason."""
    from riskagent_agenticrag.agents.agentic_rag_runner import run_agentic_rag

    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.invoke = MagicMock(side_effect=RuntimeError("LLM down"))
    mock_build_llm.return_value = mock_llm

    retriever = MagicMock()
    result = run_agentic_rag(question="test", retriever=retriever, max_tool_calls=2)

    assert result["status"] == "error"
    assert result["failure_reason"] is not None
    assert result["failure_reason"]["stage"] == "agent_loop"
