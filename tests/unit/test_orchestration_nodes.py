"""Unit tests for orchestration nodes."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**overrides) -> dict:
    """Create minimal AgenticState dict for testing."""
    base = {
        "question": "What is FRTB?",
        "request_id": "test-req-001",
        "run_id": "test-run-001",
        "max_rounds": 2,
        "retriever": MagicMock(invoke=MagicMock(return_value=[])),
        "current_query": "",
        "improved_query": "",
        "current_round": 0,
        "docs": [],
        "critique_reason": "",
        "should_continue": False,
        "answer": "",
        "citations": [],
        "tool_traces": [],
        "decision_log": [],
        "status": "ok",
        "failure_reason": None,
        "debug": {},
        "trace": {"nodes": [], "events": []},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Node: rewrite
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.rewrite_query",
       return_value="rewritten FRTB query")
def test_node_rewrite_sets_current_query(mock_rw):
    from riskagent_agenticrag.orchestration.nodes import node_rewrite

    state = _make_state()
    result = node_rewrite(state)

    assert result["current_query"] == "rewritten FRTB query"
    assert result["current_round"] == 0
    mock_rw.assert_called_once_with("What is FRTB?")


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.rewrite_query",
       return_value="q2")
def test_node_rewrite_appends_decision_log(mock_rw):
    from riskagent_agenticrag.orchestration.nodes import node_rewrite

    state = _make_state()
    result = node_rewrite(state)

    assert len(result["decision_log"]) == 1
    assert result["decision_log"][0]["step_id"] == "rewrite"


# ---------------------------------------------------------------------------
# Node: retrieve_and_critique
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_and_critique_sufficient(mock_critique, mock_grade, mock_extract):
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    mock_doc = MagicMock(page_content="FRTB info", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[mock_doc]))
    mock_critique.return_value = (True, "", "docs are sufficient")
    grade_mock = MagicMock()
    grade_mock.isrel = 0.9
    mock_grade.return_value = MagicMock(
        sufficient=True, reason="ok", top_isrel=0.9, avg_isrel=0.8,
        grades=[grade_mock]
    )

    state = _make_state(retriever=retriever, current_query="FRTB query")
    result = node_retrieve_and_critique(state)

    assert result["should_continue"] is False
    assert result["current_round"] == 1
    assert len(result["docs"]) == 1


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_and_critique_insufficient_continues(mock_critique, mock_grade, mock_extract):
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    mock_critique.return_value = (False, "try broader terms", "low relevance")
    mock_grade.return_value = MagicMock(
        sufficient=False, reason="low", top_isrel=0.3, avg_isrel=0.2,
        grades=[]
    )

    state = _make_state(retriever=retriever, current_query="narrow q", max_rounds=3)
    result = node_retrieve_and_critique(state)

    assert result["should_continue"] is True
    assert result["improved_query"] == "try broader terms"


# ---------------------------------------------------------------------------
# Node: revise_query
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_node_revise_query_uses_improved():
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    state = _make_state(current_query="old q", improved_query="better q")
    result = node_revise_query(state)

    assert result["current_query"] == "better q"


@pytest.mark.unit
def test_node_revise_query_falls_back_to_question():
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    state = _make_state(current_query="old q", improved_query="")
    result = node_revise_query(state)

    assert result["current_query"] == "What is FRTB?"


# ---------------------------------------------------------------------------
# Node: synthesize_answer
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.attach_citations_to_each_paragraph",
       return_value="answer [1]")
@patch("riskagent_agenticrag.orchestration.nodes.extract_citations", return_value=[{"source": "a.pdf"}])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.synthesize_answer",
       return_value="raw answer")
def test_node_synthesize_answer(mock_synth, mock_cite, mock_attach):
    from riskagent_agenticrag.orchestration.nodes import node_synthesize_answer

    doc = MagicMock(page_content="content", metadata={})
    state = _make_state(docs=[doc])
    result = node_synthesize_answer(state)

    assert result["answer"] == "answer [1]"
    assert result["citations"] == [{"source": "a.pdf"}]
    mock_synth.assert_called_once()


# ---------------------------------------------------------------------------
# Node: validate_and_save
# ---------------------------------------------------------------------------

@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/art.json")
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": True, "message": "", "category": ""})
def test_node_validate_and_save_ok(mock_gen, mock_ev, mock_claims, mock_num, mock_val, mock_save):
    from riskagent_agenticrag.orchestration.nodes import node_validate_and_save

    state = _make_state(answer="good answer", docs=[], citations=[])
    result = node_validate_and_save(state)

    assert result["status"] == "ok"
    assert result["failure_reason"] is None


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", side_effect=IOError("disk full"))
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value={"category": "hallucination", "message": "bad"})
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": False, "message": "fail", "category": "hallucination"})
@patch.dict("os.environ", {"RISKAGENT_ENABLE_LLM_APPEAL": "false"})
def test_node_validate_and_save_failure_with_artifact_error(mock_gen, mock_ev, mock_claims, mock_num, mock_val, mock_save):
    from riskagent_agenticrag.orchestration.nodes import node_validate_and_save

    state = _make_state(answer="bad answer", docs=[], citations=[])
    result = node_validate_and_save(state)

    assert result["status"] == "failed"
    assert result["failure_reason"]["category"] == "hallucination"
    assert "artifact_error" in result["debug"]


# ---------------------------------------------------------------------------
# Conditional edge: should_continue_retrieval
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_should_continue_retrieval_true():
    from riskagent_agenticrag.orchestration.nodes import should_continue_retrieval

    state = _make_state(should_continue=True)
    assert should_continue_retrieval(state) == "revise_query"


@pytest.mark.unit
def test_should_continue_retrieval_false():
    from riskagent_agenticrag.orchestration.nodes import should_continue_retrieval

    state = _make_state(should_continue=False)
    assert should_continue_retrieval(state) == "synthesize_answer"
