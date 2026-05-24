"""Unit tests for orchestration LangGraph runner."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, ANY


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_graph_has_expected_nodes():
    """Graph should contain all 5 node names."""
    from riskagent_agenticrag.orchestration.langgraph_runner import build_langgraph_agentic_loop

    graph = build_langgraph_agentic_loop()
    graph_obj = graph.get_graph()
    node_ids = {n.id for n in graph_obj.nodes.values() if hasattr(n, "id")}

    for expected in ("rewrite", "retrieve_and_critique", "revise_query",
                     "synthesize_answer", "validate_and_save"):
        assert expected in node_ids, f"Missing node: {expected}"


@pytest.mark.unit
def test_build_graph_entry_point_is_rewrite():
    """Entry point should route to rewrite node."""
    from riskagent_agenticrag.orchestration.langgraph_runner import build_langgraph_agentic_loop

    graph = build_langgraph_agentic_loop()
    graph_obj = graph.get_graph()
    # __start__ node should have edge to rewrite
    start_edges = [e for e in graph_obj.edges if e[0] == "__start__"]
    assert any(e[1] == "rewrite" for e in start_edges)


@pytest.mark.unit
def test_build_graph_has_conditional_edge_from_retrieve():
    """retrieve_and_critique should have conditional edges."""
    from riskagent_agenticrag.orchestration.langgraph_runner import build_langgraph_agentic_loop

    graph = build_langgraph_agentic_loop()
    graph_obj = graph.get_graph()
    retrieve_targets = {e[1] for e in graph_obj.edges if e[0] == "retrieve_and_critique"}
    assert "revise_query" in retrieve_targets or "synthesize_answer" in retrieve_targets


@pytest.mark.unit
def test_build_graph_revise_loops_back():
    """revise_query should connect back to retrieve_and_critique."""
    from riskagent_agenticrag.orchestration.langgraph_runner import build_langgraph_agentic_loop

    graph = build_langgraph_agentic_loop()
    graph_obj = graph.get_graph()
    revise_targets = {e[1] for e in graph_obj.edges if e[0] == "revise_query"}
    assert "retrieve_and_critique" in revise_targets


@pytest.mark.unit
def test_build_graph_validate_ends():
    """validate_and_save should connect to __end__."""
    from riskagent_agenticrag.orchestration.langgraph_runner import build_langgraph_agentic_loop

    graph = build_langgraph_agentic_loop()
    graph_obj = graph.get_graph()
    validate_targets = {e[1] for e in graph_obj.edges if e[0] == "validate_and_save"}
    assert "__end__" in validate_targets


# ---------------------------------------------------------------------------
# Runner tests (full pipeline with mocks)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/art.json")
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": True, "message": "", "category": ""})
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs")
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.extract_citations", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives")
def test_run_langgraph_agentic_chat_returns_expected_keys(
    mock_prims, mock_cite, mock_extract, mock_grade, mock_gen,
    mock_num, mock_val, mock_save
):
    from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat

    mock_prims.rewrite_query.return_value = "rewritten"
    mock_prims.critique_retrieval.return_value = (True, "", "ok")
    mock_prims.synthesize_answer.return_value = "final answer"
    mock_prims.attach_citations_to_each_paragraph.return_value = "final answer"
    mock_prims.build_evidence_set_from_docs.return_value = []
    mock_prims.build_claims_from_answer.return_value = []
    mock_grade.return_value = MagicMock(
        sufficient=True, reason="ok", top_isrel=0.9, avg_isrel=0.8, grades=[]
    )

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    result = run_langgraph_agentic_chat("What is FRTB?", retriever, max_rounds=2)

    assert "answer" in result
    assert "status" in result
    assert "decision_log" in result
    assert result["status"] == "ok"
    assert result["answer"] == "final answer"


# ---------------------------------------------------------------------------
# Max rounds loop logic
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/a.json")
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": True, "message": "", "category": ""})
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs")
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.extract_citations", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives")
def test_max_rounds_stops_retrieval_loop(
    mock_prims, mock_cite, mock_extract, mock_grade, mock_gen,
    mock_num, mock_val, mock_save
):
    """Even if critique says insufficient, loop stops at max_rounds."""
    from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat

    mock_prims.rewrite_query.return_value = "q"
    # Always return insufficient to force looping
    mock_prims.critique_retrieval.return_value = (False, "need more", "bad")
    mock_prims.synthesize_answer.return_value = "ans"
    mock_prims.attach_citations_to_each_paragraph.return_value = "ans"
    mock_prims.build_evidence_set_from_docs.return_value = []
    mock_prims.build_claims_from_answer.return_value = []
    mock_grade.return_value = MagicMock(
        sufficient=False, reason="bad", top_isrel=0.2, avg_isrel=0.1, grades=[]
    )

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    result = run_langgraph_agentic_chat("question", retriever, max_rounds=2)

    # Should still produce an answer (loop terminated by max_rounds)
    assert result["answer"] == "ans"
    # retrieve was called max_rounds times
    assert retriever.invoke.call_count == 2


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_state_transition_rewrite_to_retrieve():
    """After rewrite, state has current_query set for retrieval."""
    from riskagent_agenticrag.orchestration.nodes import node_rewrite

    with patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.rewrite_query",
               return_value="expanded query"):
        state = {
            "question": "Q", "request_id": "r1", "run_id": "r1",
            "max_rounds": 2, "retriever": MagicMock(),
            "current_query": "", "improved_query": "", "current_round": 0,
            "docs": [], "critique_reason": "", "should_continue": False,
            "answer": "", "citations": [], "tool_traces": [], "decision_log": [],
            "status": "ok", "failure_reason": None, "debug": {},
            "trace": {"nodes": [], "events": []},
        }
        result = node_rewrite(state)
        # Ready for retrieve_and_critique
        assert result["current_query"] == "expanded query"
        assert result["current_round"] == 0


# ---------------------------------------------------------------------------
# Visualize (mermaid fallback)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_visualize_graph_mermaid_returns_string():
    from riskagent_agenticrag.orchestration.langgraph_runner import visualize_graph_mermaid

    mermaid = visualize_graph_mermaid()
    assert isinstance(mermaid, str)
    assert len(mermaid) > 10
