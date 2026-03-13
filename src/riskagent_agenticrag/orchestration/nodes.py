"""Agentic loop 节点 -- 每个函数对应 LangGraph 中的一个 node."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal, Optional

from riskagent_agenticrag.agents.data_agent import run_data_agent
from riskagent_agenticrag.artifacts.storage import save_artifact
from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.contracts.structured import StructuredRequest
from riskagent_agenticrag.orchestration.state import AgenticState
from riskagent_agenticrag.orchestration.trace import (
    _doc_trace_row,
    _ensure_trace,
    _trace_node_end,
    _trace_node_start,
)
from riskagent_agenticrag.rag import agentic_primitives
from riskagent_agenticrag.rag.pipeline import extract_citations
from riskagent_agenticrag.rag.self_rag import grade_docs, grade_generation, should_require_numeric_backing
from riskagent_agenticrag.validators.gates import validate_response


# ---------------------------------------------------------------------------
# Node: rewrite
# ---------------------------------------------------------------------------

def node_rewrite(state: AgenticState) -> AgenticState:
    """Node: rewrite query for better retrieval."""
    start_ms = _trace_node_start(state, "rewrite", {"question": state.get("question", "")})
    question = state["question"]
    rewritten = agentic_primitives.rewrite_query(question)

    state["current_query"] = rewritten
    state["improved_query"] = ""
    state["current_round"] = 0
    state["decision_log"] = state.get("decision_log", [])
    state["decision_log"].append({
        "step_id": "rewrite",
        "agent": "AgenticLoop",
        "rationale": "rewrite user question for retrieval",
        "chosen": rewritten,
        "alternatives": [question],
    })

    _trace_node_end(state, "rewrite", start_ms, {"current_query": rewritten})
    return state


# ---------------------------------------------------------------------------
# Node: retrieve_and_critique (含 Self-RAG 文档评分)
# ---------------------------------------------------------------------------

def node_retrieve_and_critique(state: AgenticState) -> AgenticState:
    """Node: retrieve docs and critique quality."""
    start_ms = _trace_node_start(
        state,
        "retrieve_and_critique",
        {
            "round": int(state.get("current_round", 0) + 1),
            "current_query": state.get("current_query", ""),
        },
    )
    retriever = state["retriever"]
    current_query = state["current_query"]
    question = state["question"]
    max_rounds = state["max_rounds"]
    current_round = state.get("current_round", 0)

    docs = retriever.invoke(current_query)

    self_rag_enabled = os.getenv("RISKAGENT_SELF_RAG", "").lower().strip() in {"true", "1", "yes"}
    self_sufficient = False
    if self_rag_enabled:
        g = grade_docs(question=question, docs=docs)
        self_sufficient = bool(g.sufficient)
        debug = state.get("debug") or {}
        self_rag = debug.get("self_rag")
        if not isinstance(self_rag, dict):
            self_rag = {"enabled": True, "rounds": []}
        rounds = self_rag.get("rounds")
        if not isinstance(rounds, list):
            rounds = []
        rounds.append(
            {
                "round": int(current_round + 1),
                "query": str(current_query),
                "grade": {
                    "sufficient": bool(g.sufficient),
                    "reason": str(g.reason),
                    "top_isrel": float(g.top_isrel),
                    "avg_isrel": float(g.avg_isrel),
                    "docs": [gd.__dict__ for gd in g.grades],
                },
            }
        )
        self_rag["rounds"] = rounds
        debug["self_rag"] = self_rag
        state["debug"] = debug

        decision_log = state.get("decision_log", [])
        decision_log.append(
            {
                "step_id": f"self_rag_grade_docs_round_{int(current_round + 1)}",
                "agent": "SelfRAG",
                "rationale": str(g.reason),
                "chosen": "sufficient" if g.sufficient else "insufficient",
                "alternatives": [f"top_isrel={g.top_isrel:.3f}"],
            }
        )
        state["decision_log"] = decision_log

    sufficient, improved_query, critique_reason = agentic_primitives.critique_retrieval(question, docs)
    next_round = current_round + 1
    should_continue = (not bool(sufficient or self_sufficient)) and (next_round < max_rounds)

    state["docs"] = docs
    state["critique_reason"] = critique_reason
    state["improved_query"] = improved_query
    state["should_continue"] = should_continue
    state["current_round"] = next_round

    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": f"retrieve_round_{next_round}",
        "agent": "AgenticLoop",
        "rationale": critique_reason or "retrieval done",
        "chosen": "continue" if should_continue else "stop",
        "alternatives": [f"docs_count={len(docs)}"],
    })
    state["decision_log"] = decision_log

    snippet_chars = int(os.getenv("RISKAGENT_TRACE_SNIPPET_CHARS", "240"))
    doc_refs: list[dict[str, Any]] = []
    for d in docs[:8]:
        doc_refs.append(_doc_trace_row(d, snippet_chars=snippet_chars))
    _trace_node_end(
        state,
        "retrieve_and_critique",
        start_ms,
        {
            "docs_count": len(docs),
            "should_continue": bool(should_continue),
            "critique_reason": str(critique_reason),
            "improved_query": str(improved_query),
            "docs": doc_refs,
        },
    )
    return state


# ---------------------------------------------------------------------------
# Node: revise_query
# ---------------------------------------------------------------------------

def node_revise_query(state: AgenticState) -> AgenticState:
    """Node: revise query based on critique."""
    start_ms = _trace_node_start(
        state,
        "revise_query",
        {"current_query": state.get("current_query", ""), "improved_query": state.get("improved_query", "")},
    )
    question = state["question"]
    current_query = state["current_query"]
    improved_query = str(state.get("improved_query", "")).strip()
    next_query = improved_query or question
    state["current_query"] = next_query

    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": "revise_query",
        "agent": "AgenticLoop",
        "rationale": "revise query based on critique",
        "chosen": next_query,
        "alternatives": [current_query],
    })
    state["decision_log"] = decision_log

    _trace_node_end(state, "revise_query", start_ms, {"next_query": next_query})
    return state


# ---------------------------------------------------------------------------
# Node: decide_tool_use
# ---------------------------------------------------------------------------

def node_decide_tool_use(state: AgenticState) -> AgenticState:
    """Node: decide whether to call tool."""
    start_ms = _trace_node_start(state, "decide_tool_use", {"question": state.get("question", "")})
    question = state["question"]
    should_call, tool_args, tool_reason = agentic_primitives.decide_tool_use(question)

    state["should_call_tool"] = should_call
    state["tool_args"] = tool_args
    state["tool_reason"] = tool_reason
    state["tool_traces"] = state.get("tool_traces", [])

    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": "tool_decision",
        "agent": "AgenticLoop",
        "rationale": tool_reason or "decide tool use",
        "chosen": "call" if should_call else "skip",
        "alternatives": [json.dumps(tool_args, ensure_ascii=False)],
    })
    state["decision_log"] = decision_log

    _trace_node_end(
        state,
        "decide_tool_use",
        start_ms,
        {"should_call_tool": bool(should_call), "tool_args": tool_args, "tool_reason": str(tool_reason)},
    )
    return state


# ---------------------------------------------------------------------------
# Node: call_tool
# ---------------------------------------------------------------------------

def node_call_tool(state: AgenticState) -> AgenticState:
    """Node: call tool and collect traces."""
    start_ms = _trace_node_start(state, "call_tool", {"tool_args": state.get("tool_args", {})})
    question = state["question"]
    tool_args = state["tool_args"]

    desk = str(tool_args.get("desk", "")).strip()
    as_of = str(tool_args.get("as_of", "")).strip() or agentic_primitives.utc_today_date()
    abs_delta_limit_raw = tool_args.get("abs_delta_limit", 1000000)
    try:
        abs_delta_limit = float(abs_delta_limit_raw)
    except Exception:
        abs_delta_limit = 1000000.0

    tool_output: Optional[dict[str, Any]] = None
    tool_traces = state.get("tool_traces", [])

    if desk:
        request = StructuredRequest(
            request_id=str(uuid.uuid4()),
            query=question,
            as_of=as_of,
            desk=desk,
            abs_delta_limit=abs_delta_limit,
        )
        tool_output, trace, _failure = run_data_agent(request)
        if hasattr(trace, "model_dump"):
            tool_traces.append(trace.model_dump())  # type: ignore[attr-defined]
        else:
            tool_traces.append(trace.dict())
    else:
        decision_log = state.get("decision_log", [])
        decision_log.append({
            "step_id": "tool_skip_missing_desk",
            "agent": "AgenticLoop",
            "rationale": "tool args missing desk",
            "chosen": "skip",
            "alternatives": [json.dumps(tool_args, ensure_ascii=False)],
        })
        state["decision_log"] = decision_log

    state["tool_output"] = tool_output
    state["tool_traces"] = tool_traces

    breach_count = 0
    if isinstance(tool_output, dict):
        raw_breaches = tool_output.get("breaches")
        if isinstance(raw_breaches, list):
            breach_count = len(raw_breaches)
    _trace_node_end(
        state,
        "call_tool",
        start_ms,
        {"has_output": bool(tool_output), "tool_traces_count": len(tool_traces), "breach_count": breach_count},
    )
    return state


# ---------------------------------------------------------------------------
# Node: synthesize_answer
# ---------------------------------------------------------------------------

def node_synthesize_answer(state: AgenticState) -> AgenticState:
    """Node: synthesize final answer with citations."""
    start_ms = _trace_node_start(state, "synthesize_answer", {"docs_count": len(state.get("docs") or [])})
    question = state["question"]
    docs = state["docs"]
    tool_output = state.get("tool_output")

    answer = agentic_primitives.synthesize_answer_with_tool(
        question=question,
        docs=docs,
        tool_output=tool_output,
    )
    citations = extract_citations(docs)
    answer_with_citations = agentic_primitives.attach_citations_to_each_paragraph(answer, citations)

    state["answer"] = answer_with_citations
    state["citations"] = citations

    _trace_node_end(
        state,
        "synthesize_answer",
        start_ms,
        {"answer_len": len(answer_with_citations), "citations_count": len(citations)},
    )
    return state


# ---------------------------------------------------------------------------
# LLM 申诉机制 (validate_and_save 的辅助函数)
# ---------------------------------------------------------------------------

def _llm_appeal_failure(
    question: str,
    answer: str,
    failure_reason: dict[str, Any],
    evidence_set: list[dict[str, Any]],
) -> dict[str, Any]:
    """LLM 申诉机制: 判断 gate 失败是否属于误判."""
    from riskagent_agenticrag.llm.generate import call_llm_json

    appeal_prompt = f"""你是一个质量控制审核员。请判断以下验证失败是否属于"误判"(false positive)。

原始问题: {question}

生成的回答: {answer[:800]}

验证失败的类别: {failure_reason.get('category', 'unknown')}
失败详情: {failure_reason.get('message', 'N/A')}

证据片段数量: {len(evidence_set)}

请分析:
1. 这个失败类别是否合理?
2. 回答是否真的存在所述问题?
3. 这是否可能是验证规则的过度敏感导致的误判?

以JSON格式返回:
{{
  "is_false_positive": true/false,
  "reason": "你的判断理由，1-2句话",
  "suggested_fix": "如果确实存在问题，建议如何修正（如适用）"
}}"""

    try:
        result = call_llm_json(appeal_prompt, temperature=0.0)
        return {
            "is_false_positive": result.get("is_false_positive", False),
            "reason": result.get("reason", "No reason provided"),
            "suggested_fix": result.get("suggested_fix"),
        }
    except Exception:
        return {"is_false_positive": False, "reason": "LLM appeal failed", "suggested_fix": None}


# ---------------------------------------------------------------------------
# Node: validate_and_save (含 LLM 申诉 + Self-RAG 生成评分 + artifact 落盘)
# ---------------------------------------------------------------------------

def node_validate_and_save(state: AgenticState) -> AgenticState:
    """Node: validate response and save artifact (with LLM appeal mechanism)."""
    start_ms = _trace_node_start(state, "validate_and_save", {"request_id": state.get("request_id", "")})
    answer = state["answer"]
    docs = state["docs"]
    tool_traces = state.get("tool_traces", [])
    tool_output = state.get("tool_output")

    evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=True)
    claims = agentic_primitives.build_claims_from_answer(
        answer,
        evidence_set=evidence_set,
    )

    failure_reason = validate_response(
        report=answer,
        claims=claims,
        evidence_set=evidence_set,
        tool_traces=tool_traces,
        docs=docs,
        require_numeric_backing=should_require_numeric_backing(
            question=state.get("question", ""),
            should_call_tool=bool(state.get("should_call_tool", False)),
        ),
    )

    # LLM 申诉机制: 如果验证失败, 让 LLM 判断是否为误判
    if failure_reason is not None:
        appeal_result = _llm_appeal_failure(
            question=state.get("question", ""),
            answer=answer,
            failure_reason=failure_reason,
            evidence_set=evidence_set,
        )

        if appeal_result.get("is_false_positive", False):
            failure_reason["appealed"] = True
            failure_reason["appeal_reason"] = appeal_result.get("reason", "")
            failure_reason["category"] = f"appealed_{failure_reason.get('category', 'unknown')}"
            failure_reason = None
        else:
            failure_reason["appealed"] = False
            failure_reason["appeal_reason"] = appeal_result.get("reason", "")
            if appeal_result.get("suggested_fix"):
                failure_reason["suggested_fix"] = appeal_result.get("suggested_fix")

    status = "ok" if failure_reason is None else "failed"
    state["status"] = status
    state["failure_reason"] = failure_reason
    state["claims"] = claims
    state["evidence_set"] = evidence_set

    debug_info: dict[str, Any] = {
        "final_query": state["current_query"],
        "critique_reason": state.get("critique_reason", ""),
        "tool_args": state.get("tool_args", {}),
        "tool_should_call": state.get("should_call_tool", False),
    }
    self_rag_enabled = os.getenv("RISKAGENT_SELF_RAG", "").lower().strip() in {"true", "1", "yes"}
    if self_rag_enabled:
        gen = grade_generation(failure_reason=failure_reason)
        self_rag = (state.get("debug") or {}).get("self_rag")
        if not isinstance(self_rag, dict):
            self_rag = {"enabled": True, "rounds": []}
        self_rag["generation"] = gen
        debug_info["self_rag"] = self_rag
        decision_log = state.get("decision_log", [])
        decision_log.append(
            {
                "step_id": "self_rag_grade_generation",
                "agent": "SelfRAG",
                "rationale": str(gen.get("message") or ""),
                "chosen": "ok" if bool(gen.get("ok")) else "fail",
                "alternatives": [str(gen.get("category") or "")],
            }
        )
        state["decision_log"] = decision_log

    request_id = str(state.get("request_id") or str(uuid.uuid4()))
    state["request_id"] = request_id
    request_data = {
        "question": state["question"],
        "max_rounds": state["max_rounds"],
    }
    response_data: dict[str, Any] = {
        "answer": answer,
        "citations": state["citations"],
        "claims": claims,
        "evidence_set": evidence_set,
        "decision_log": state.get("decision_log", []),
        "tool_traces": tool_traces,
        "status": status,
        "failure_reason": failure_reason,
        "debug": debug_info,
    }

    breaches: list[dict[str, Any]] = []
    if isinstance(tool_output, dict):
        raw_breaches = tool_output.get("breaches")
        if isinstance(raw_breaches, list):
            breaches = raw_breaches

    structured_evidence_set = agentic_primitives.build_evidence_set_from_docs(docs, include_text=False)

    structured_payload: dict[str, Any] = {
        "request_id": request_id,
        "report": answer,
        "breaches": breaches,
        "evidence_set": structured_evidence_set,
        "claims": claims,
        "tool_traces": tool_traces,
        "decision_log": state.get("decision_log", []),
        "status": status,
        "failure_reason": failure_reason,
    }

    try:
        retriever_version = {
            "mode": os.getenv("RISKAGENT_RETRIEVER_MODE", ""),
            "reranker_model": os.getenv("RISKAGENT_RERANKER_MODEL", ""),
            "dense_k": os.getenv("RISKAGENT_DENSE_K", ""),
            "sparse_k": os.getenv("RISKAGENT_SPARSE_K", ""),
            "rerank_k": os.getenv("RISKAGENT_RERANK_K", ""),
            "persist_dir": str(settings.paths.milvus_lite_dir),
        }
        trace = _ensure_trace(state)
        trace["request_id"] = str(request_id)
        trace["run_id"] = str(state.get("run_id", ""))
        trace["model_id"] = str(settings.llm.model or "")
        trace["prompt_version"] = str(os.getenv("RISKAGENT_PROMPT_VERSION", "v1"))
        trace["retriever_version"] = retriever_version
        trace["final"] = {"status": status, "failure_reason": failure_reason}
        artifact_path = save_artifact(
            request_id,
            request_data,
            response_data,
            structured_response_data=structured_payload,
            trace_data=trace,
        )
        debug_info["artifact_path"] = artifact_path
        debug_info["artifact_bundle_dir"] = str(Path(str(artifact_path)).with_suffix(""))
        debug_info["retriever_version"] = retriever_version
    except Exception as e:
        debug_info["artifact_error"] = str(e)

    debug_info["request_id"] = str(request_id)
    debug_info["run_id"] = str(state.get("run_id", ""))
    debug_info["model_id"] = str(settings.llm.model or "")
    debug_info["prompt_version"] = str(os.getenv("RISKAGENT_PROMPT_VERSION", "v1"))
    state["debug"] = debug_info

    _trace_node_end(
        state,
        "validate_and_save",
        start_ms,
        {"status": status, "failure_reason": failure_reason, "claims_count": len(claims), "evidence_count": len(evidence_set)},
    )
    return state


# ---------------------------------------------------------------------------
# 条件边 (conditional edges)
# ---------------------------------------------------------------------------

def should_continue_retrieval(state: AgenticState) -> Literal["revise_query", "decide_tool_use"]:
    """Conditional edge: should continue retrieval or move to tool decision."""
    if state.get("should_continue", False):
        return "revise_query"
    return "decide_tool_use"


def should_call_tool(state: AgenticState) -> Literal["call_tool", "synthesize_answer"]:
    """Conditional edge: should call tool or directly synthesize answer."""
    if state.get("should_call_tool", False):
        return "call_tool"
    return "synthesize_answer"
