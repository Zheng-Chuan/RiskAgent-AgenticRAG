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

    # 使用 moderate 查询 (>=15 字符且无复杂信号) 确保 TARG 判定 needs_rewrite=True
    state = _make_state(question="What is FRTB delta capital charge")
    result = node_rewrite(state)

    assert result["current_query"] == "rewritten FRTB query"
    assert result["current_round"] == 0
    mock_rw.assert_called_once_with("What is FRTB delta capital charge")


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
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
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
        crag_tier="sufficient", grades=[grade_mock]
    )

    state = _make_state(retriever=retriever, current_query="FRTB query")
    result = node_retrieve_and_critique(state)

    assert result["should_continue"] is False
    assert result["current_round"] == 1
    assert len(result["docs"]) == 1


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
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


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_and_critique_disagreement_prefers_continue_when_self_rag_only_says_sufficient(
    mock_critique, mock_grade, mock_extract
):
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    mock_doc = MagicMock(page_content="thin context", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[mock_doc]))
    mock_critique.return_value = (False, "broader FRTB definition", "context is too thin")
    mock_grade.return_value = MagicMock(
        sufficient=True, reason="ok_definition", top_isrel=0.7, avg_isrel=0.5,
        grades=[]
    )

    state = _make_state(retriever=retriever, current_query="FRTB")
    result = node_retrieve_and_critique(state)

    assert result["should_continue"] is True
    assert result["improved_query"] == "broader FRTB definition"


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_and_critique_disagreement_prefers_continue_when_self_rag_says_insufficient(
    mock_critique, mock_grade, mock_extract
):
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    mock_doc = MagicMock(page_content="partial context", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[mock_doc]))
    mock_critique.return_value = (True, "", "llm thinks enough")
    mock_grade.return_value = MagicMock(
        sufficient=False, reason="definition_coverage_thin", top_isrel=0.4, avg_isrel=0.3,
        grades=[]
    )

    state = _make_state(retriever=retriever, current_query="FRTB")
    result = node_retrieve_and_critique(state)

    assert result["should_continue"] is True


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


# ---------------------------------------------------------------------------
# 辅助函数: _extract_doc_score / _seal_rag_capacity / _infer_retriever_k
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_doc_score_rerank_priority():
    """rerank_score 应优先于 rrf_score / coarse_score."""
    from riskagent_agenticrag.orchestration.nodes import _extract_doc_score
    from langchain_core.documents import Document

    d = Document(page_content="x", metadata={"rerank_score": 0.9, "rrf_score": 0.5, "coarse_score": 0.3})
    score, src = _extract_doc_score(d)
    assert score == 0.9
    assert src == "rerank"


@pytest.mark.unit
def test_extract_doc_score_rrf_when_no_rerank():
    """无 rerank_score 时应回退到 rrf_score."""
    from riskagent_agenticrag.orchestration.nodes import _extract_doc_score
    from langchain_core.documents import Document

    d = Document(page_content="x", metadata={"rrf_score": 0.5, "coarse_score": 0.3})
    score, src = _extract_doc_score(d)
    assert score == 0.5
    assert src == "hybrid"


@pytest.mark.unit
def test_extract_doc_score_coarse_when_no_rrf():
    """无 rrf_score 时应回退到 coarse_score."""
    from riskagent_agenticrag.orchestration.nodes import _extract_doc_score
    from langchain_core.documents import Document

    d = Document(page_content="x", metadata={"coarse_score": 0.3})
    score, src = _extract_doc_score(d)
    assert score == 0.3
    assert src == "coarse"


@pytest.mark.unit
def test_extract_doc_score_unknown_when_no_scores():
    """无任何分数时应返回 0.0 / unknown."""
    from riskagent_agenticrag.orchestration.nodes import _extract_doc_score
    from langchain_core.documents import Document

    d = Document(page_content="x", metadata={})
    score, src = _extract_doc_score(d)
    assert score == 0.0
    assert src == "unknown"


@pytest.mark.unit
def test_seal_rag_capacity_reads_settings():
    """_seal_rag_capacity 应读取 settings.features.seal_rag_budget."""
    from riskagent_agenticrag.orchestration.nodes import _seal_rag_capacity

    with patch("riskagent_agenticrag.orchestration.nodes.settings") as mock_settings:
        mock_settings.features.seal_rag_budget = 7
        assert _seal_rag_capacity() == 7


@pytest.mark.unit
def test_seal_rag_capacity_falls_back_on_error():
    """settings 读取异常时应回退到默认 5."""
    from riskagent_agenticrag.orchestration.nodes import _seal_rag_capacity

    with patch("riskagent_agenticrag.orchestration.nodes.settings") as mock_settings:
        type(mock_settings.features).seal_rag_budget = property(lambda s: (_ for _ in ()).throw(RuntimeError("x")))
        assert _seal_rag_capacity() == 5


@pytest.mark.unit
def test_infer_retriever_k_reads_final_k():
    """_infer_retriever_k 应优先读取 _config.final_k."""
    from riskagent_agenticrag.orchestration.nodes import _infer_retriever_k

    retriever = MagicMock()
    retriever._config = MagicMock(final_k=12)
    assert _infer_retriever_k(retriever) == 12


@pytest.mark.unit
def test_infer_retriever_k_recurses_to_base():
    """外层无 config 时应递归 _base."""
    from riskagent_agenticrag.orchestration.nodes import _infer_retriever_k

    inner = MagicMock()
    inner._config = MagicMock(k=20)
    retriever = MagicMock()
    retriever._config = None
    retriever._base = inner
    assert _infer_retriever_k(retriever) == 20


@pytest.mark.unit
def test_infer_retriever_k_defaults_to_8():
    """推断失败时应回退到默认 8."""
    from riskagent_agenticrag.orchestration.nodes import _infer_retriever_k

    retriever = MagicMock()
    retriever._config = None
    retriever._base = None
    assert _infer_retriever_k(retriever) == 8


# ---------------------------------------------------------------------------
# 辅助函数: _invoke_without_fanout
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invoke_without_fanout_digs_to_hybrid():
    """_invoke_without_fanout 应下钻到 HybridRetriever."""
    from riskagent_agenticrag.orchestration.nodes import _invoke_without_fanout

    hybrid = MagicMock()
    hybrid.invoke.return_value = ["doc1", "doc2"]
    query_intel = MagicMock(_base=hybrid)
    retriever = MagicMock(_base=query_intel)

    result = _invoke_without_fanout(retriever, "query")
    assert result == ["doc1", "doc2"]
    hybrid.invoke.assert_called_once_with("query")


@pytest.mark.unit
def test_invoke_without_fanout_falls_back_to_retriever():
    """下钻失败时应退回原检索器."""
    from riskagent_agenticrag.orchestration.nodes import _invoke_without_fanout

    retriever = MagicMock()
    retriever._base = None
    retriever.invoke.return_value = ["fallback_doc"]

    result = _invoke_without_fanout(retriever, "query")
    assert result == ["fallback_doc"]


# ---------------------------------------------------------------------------
# TARG 门控: simple 查询跳过检索
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_route_after_rewrite_simple_query_skips_retrieval():
    """simple 查询应路由到 synthesize_answer."""
    from riskagent_agenticrag.orchestration.nodes import route_after_rewrite

    state = _make_state(query_complexity={"level": "simple", "needs_retrieval": False})
    assert route_after_rewrite(state) == "synthesize_answer"


@pytest.mark.unit
def test_route_after_rewrite_moderate_query_enters_retrieval():
    """非 simple 查询应进入检索."""
    from riskagent_agenticrag.orchestration.nodes import route_after_rewrite

    state = _make_state(query_complexity={"level": "moderate", "needs_retrieval": True})
    assert route_after_rewrite(state) == "retrieve_and_critique"


@pytest.mark.unit
def test_should_continue_retrieval_simple_query_skips_revise():
    """simple 查询误入检索节点时应直接转合成."""
    from riskagent_agenticrag.orchestration.nodes import should_continue_retrieval

    state = _make_state(
        should_continue=True,
        query_complexity={"level": "simple", "needs_retrieval": False},
    )
    assert should_continue_retrieval(state) == "synthesize_answer"


# ---------------------------------------------------------------------------
# CRAG 降级策略: expand_topk / rewrite_and_retrieve
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.crag_strategies.expand_retrieval")
def test_node_revise_query_expand_topk_action(mock_expand):
    """failure_reason action=expand_topk 时应调用 expand_retrieval."""
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    mock_expand.return_value = [MagicMock(page_content="expanded")]
    retriever = MagicMock()
    state = _make_state(
        current_query="old q",
        improved_query="",
        retriever=retriever,
        failure_reason={"reason": "crag_irrelevant", "action": "expand_topk"},
    )
    result = node_revise_query(state)
    assert result["current_query"] == "old q"
    mock_expand.assert_called_once()


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.crag_strategies.expand_retrieval", side_effect=RuntimeError("fail"))
def test_node_revise_query_expand_topk_fallback(mock_expand):
    """expand_retrieval 抛异常时应回退到普通 revise."""
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    retriever = MagicMock()
    state = _make_state(
        current_query="old q",
        improved_query="better q",
        retriever=retriever,
        failure_reason={"reason": "crag_irrelevant", "action": "expand_topk"},
    )
    result = node_revise_query(state)
    assert result["current_query"] == "better q"


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.crag_strategies.rewrite_and_retrieve")
def test_node_revise_query_rewrite_and_retrieve_action(mock_rw):
    """failure_reason action=rewrite_and_retrieve 时应调用 rewrite_and_retrieve."""
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    mock_rw.return_value = ("new query", [MagicMock(page_content="new")])
    retriever = MagicMock()
    state = _make_state(
        current_query="old q",
        improved_query="",
        retriever=retriever,
        failure_reason={"reason": "crag_insufficient", "action": "rewrite_and_retrieve"},
    )
    result = node_revise_query(state)
    assert result["current_query"] == "new query"
    mock_rw.assert_called_once()


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.crag_strategies.rewrite_and_retrieve", side_effect=RuntimeError("fail"))
def test_node_revise_query_rewrite_fallback(mock_rw):
    """rewrite_and_retrieve 抛异常时应回退到普通 revise."""
    from riskagent_agenticrag.orchestration.nodes import node_revise_query

    retriever = MagicMock()
    state = _make_state(
        current_query="old q",
        improved_query="better q",
        retriever=retriever,
        failure_reason={"reason": "crag_insufficient", "action": "rewrite_and_retrieve"},
    )
    result = node_revise_query(state)
    assert result["current_query"] == "better q"


# ---------------------------------------------------------------------------
# LLM 申诉机制
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_appeal_enabled_reads_env():
    """_appeal_enabled 应读取 RISKAGENT_ENABLE_LLM_APPEAL 环境变量."""
    import os
    from riskagent_agenticrag.orchestration.nodes import _appeal_enabled

    with patch.dict(os.environ, {"RISKAGENT_ENABLE_LLM_APPEAL": "true"}):
        assert _appeal_enabled() is True

    with patch.dict(os.environ, {"RISKAGENT_ENABLE_LLM_APPEAL": "false"}):
        assert _appeal_enabled() is False


@pytest.mark.unit
@patch("riskagent_agenticrag.llm.generate.call_llm_json", side_effect=RuntimeError("llm fail"))
def test_llm_appeal_failure_handles_exception(mock_llm):
    """LLM 申诉调用失败时应返回默认结果."""
    from riskagent_agenticrag.orchestration.nodes import _llm_appeal_failure

    result = _llm_appeal_failure("question", "answer", {"category": "test"}, [])
    assert result["is_false_positive"] is False
    assert result["reason"] == "LLM appeal failed"


@pytest.mark.unit
@patch("riskagent_agenticrag.llm.generate.call_llm_json")
def test_llm_appeal_false_positive_overrides(mock_llm):
    """申诉判定为误判时应返回 is_false_positive=True."""
    from riskagent_agenticrag.orchestration.nodes import _llm_appeal_failure

    mock_llm.return_value = {"is_false_positive": True, "reason": "规则误判", "suggested_fix": None}
    result = _llm_appeal_failure("q", "a", {"category": "x"}, [])
    assert result["is_false_positive"] is True


# ---------------------------------------------------------------------------
# node_validate_and_save: 启用 LLM 申诉
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/art.json")
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value={"category": "bad", "message": "fail"})
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": True, "message": "", "category": ""})
@patch("riskagent_agenticrag.orchestration.nodes.get_last_token_usage", return_value={"prompt": 10, "completion": 5})
@patch("riskagent_agenticrag.orchestration.nodes._llm_appeal_failure")
@patch.dict("os.environ", {"RISKAGENT_ENABLE_LLM_APPEAL": "true"})
def test_node_validate_and_save_appeal_overrides_failure(
    mock_appeal, mock_tok, mock_gen, mock_ev, mock_claims, mock_num, mock_val, mock_save,
):
    """启用 appeal 且判定为误判时应将 failure_reason 置为 None."""
    from riskagent_agenticrag.orchestration.nodes import node_validate_and_save

    mock_appeal.return_value = {"is_false_positive": True, "reason": "误判", "suggested_fix": None}
    state = _make_state(answer="bad answer", docs=[], citations=[])
    result = node_validate_and_save(state)
    assert result["status"] == "ok"
    assert result["failure_reason"] is None


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/art.json")
@patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value={"category": "bad", "message": "fail"})
@patch("riskagent_agenticrag.orchestration.nodes.should_require_numeric_backing", return_value=False)
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[])
@patch("riskagent_agenticrag.orchestration.nodes.grade_generation", return_value={"ok": False, "message": "f", "category": "bad"})
@patch("riskagent_agenticrag.orchestration.nodes.get_last_token_usage", return_value={"prompt": 10, "completion": 5})
@patch("riskagent_agenticrag.orchestration.nodes._llm_appeal_failure")
@patch.dict("os.environ", {"RISKAGENT_ENABLE_LLM_APPEAL": "true"})
def test_node_validate_and_save_appeal_not_false_positive_keeps_failure(
    mock_appeal, mock_tok, mock_gen, mock_ev, mock_claims, mock_num, mock_val, mock_save,
):
    """申诉判定非误判时应保留 failure_reason."""
    from riskagent_agenticrag.orchestration.nodes import node_validate_and_save

    mock_appeal.return_value = {"is_false_positive": False, "reason": "确实有问题", "suggested_fix": "改这里"}
    state = _make_state(answer="bad answer", docs=[], citations=[])
    result = node_validate_and_save(state)
    assert result["status"] == "failed"
    assert result["failure_reason"]["category"] == "bad"
    assert result["failure_reason"]["appealed"] is False


# ---------------------------------------------------------------------------
# node_retrieve_and_critique: CRAG irrelevant / insufficient 档
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_crag_irrelevant_triggers_expand(mock_critique, mock_grade, mock_extract):
    """CRAG irrelevant 档应设置 failure_reason action=expand_topk."""
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    mock_critique.return_value = (False, "", "low relevance")
    mock_grade.return_value = MagicMock(
        sufficient=False, reason="irrelevant", top_isrel=0.1, avg_isrel=0.05,
        crag_tier="irrelevant", grades=[],
    )

    state = _make_state(retriever=retriever, current_query="q", max_rounds=3)
    result = node_retrieve_and_critique(state)
    assert result["should_continue"] is True
    assert result["failure_reason"]["action"] == "expand_topk"


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_crag_irrelevant_stops_at_max_rounds(mock_critique, mock_grade, mock_extract):
    """CRAG irrelevant 档到达 max_rounds 时应停止."""
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    mock_critique.return_value = (False, "", "low")
    mock_grade.return_value = MagicMock(
        sufficient=False, reason="irrelevant", top_isrel=0.1, avg_isrel=0.05,
        crag_tier="irrelevant", grades=[],
    )

    state = _make_state(retriever=retriever, current_query="q", max_rounds=1, current_round=0)
    result = node_retrieve_and_critique(state)
    assert result["should_continue"] is False


@pytest.mark.unit
@patch("riskagent_agenticrag.orchestration.nodes.extract_structured_request", return_value=None)
@patch("riskagent_agenticrag.orchestration.nodes.grade_docs_crag")
@patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.critique_retrieval")
def test_node_retrieve_self_rag_disabled_uses_critique(mock_critique, mock_grade, mock_extract):
    """关闭 Self-RAG 时应使用 LLM critique 二档逻辑."""
    import os
    from riskagent_agenticrag.orchestration.nodes import node_retrieve_and_critique

    retriever = MagicMock(invoke=MagicMock(return_value=[]))
    mock_critique.return_value = (False, "try broader", "low relevance")
    mock_grade.return_value = MagicMock(
        sufficient=True, reason="ok", top_isrel=0.9, avg_isrel=0.8,
        crag_tier="sufficient", grades=[],
    )

    with patch.dict(os.environ, {"RISKAGENT_SELF_RAG": "false"}):
        state = _make_state(retriever=retriever, current_query="q", max_rounds=3)
        result = node_retrieve_and_critique(state)
        # Self-RAG 关闭, critique 说不充分, 应继续
        assert result["should_continue"] is True
        assert result["failure_reason"] is None


# ---------------------------------------------------------------------------
# node_rewrite: TARG 跳过 rewrite
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_node_rewrite_skips_rewrite_for_simple_query():
    """simple 查询应跳过 rewrite, 直接用原始 question."""
    from riskagent_agenticrag.orchestration.nodes import node_rewrite
    from riskagent_agenticrag.rag.query_router import QueryComplexity

    simple_qc = QueryComplexity(
        level="simple", needs_retrieval=False, needs_rewrite=False,
        needs_fanout=False, confidence=0.9, reason="simple",
    )
    with patch("riskagent_agenticrag.orchestration.nodes.assess_query_complexity", return_value=simple_qc):
        state = _make_state(question="what is 1+1")
        result = node_rewrite(state)
        assert result["current_query"] == "what is 1+1"
        assert result["query_complexity"]["level"] == "simple"


@pytest.mark.unit
def test_node_rewrite_sets_skip_fanout_for_moderate():
    """moderate 查询不需要 fanout 时应设置 skip_fanout."""
    from riskagent_agenticrag.orchestration.nodes import node_rewrite
    from riskagent_agenticrag.rag.query_router import QueryComplexity

    moderate_qc = QueryComplexity(
        level="moderate", needs_retrieval=True, needs_rewrite=True,
        needs_fanout=False, confidence=0.6, reason="moderate",
    )
    with patch("riskagent_agenticrag.orchestration.nodes.assess_query_complexity", return_value=moderate_qc), \
         patch("riskagent_agenticrag.orchestration.nodes.agentic_primitives.rewrite_query", return_value="rewritten"):
        state = _make_state(question="explain delta risk")
        result = node_rewrite(state)
        assert result["skip_fanout"] is True
        assert result["current_query"] == "rewritten"
