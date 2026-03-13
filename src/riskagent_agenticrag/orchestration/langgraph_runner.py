# 中文注释: LangGraph 编排层实现
# 用途: 将 agentic loop 的各个步骤用 LangGraph 重新编排, 统一 state 和 trace

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from riskagent_agenticrag.agents.data_agent import run_data_agent
from riskagent_agenticrag.artifacts.storage import save_artifact
from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.contracts.structured import StructuredRequest
from riskagent_agenticrag.rag import agentic_primitives
from riskagent_agenticrag.rag.pipeline import extract_citations
from riskagent_agenticrag.rag.self_rag import grade_docs, grade_generation, should_require_numeric_backing
from riskagent_agenticrag.validators.gates import validate_response


class AgenticState(TypedDict, total=False):
    """LangGraph state schema for agentic RAG loop."""

    question: str
    request_id: str
    run_id: str
    max_rounds: int
    retriever: Any
    trace: dict[str, Any]

    current_query: str
    improved_query: str
    current_round: int
    docs: list[Any]
    critique_reason: str
    should_continue: bool

    should_call_tool: bool
    tool_args: dict[str, Any]
    tool_reason: str
    tool_output: Optional[dict[str, Any]]
    tool_traces: list[dict[str, Any]]

    answer: str
    citations: list[dict[str, str]]
    claims: list[dict[str, Any]]
    evidence_set: list[dict[str, Any]]
    decision_log: list[dict[str, Any]]

    status: str
    failure_reason: Optional[dict[str, Any]]
    debug: dict[str, Any]


def _ms() -> float:
    return time.time() * 1000.0


def _ensure_trace(state: AgenticState) -> dict[str, Any]:
    trace = state.get("trace")
    if not isinstance(trace, dict):
        trace = {"events": [], "nodes": []}
        state["trace"] = trace
    events = trace.get("events")
    if not isinstance(events, list):
        trace["events"] = []
    nodes = trace.get("nodes")
    if not isinstance(nodes, list):
        trace["nodes"] = []
    return trace


def _trace_node_start(state: AgenticState, name: str, payload: dict[str, Any]) -> float:
    trace = _ensure_trace(state)
    nodes = trace.get("nodes") or []
    entry = {"name": str(name), "start_ms": _ms(), "payload": dict(payload)}
    nodes.append(entry)
    trace["nodes"] = nodes
    return float(entry["start_ms"])


def _trace_node_end(state: AgenticState, name: str, start_ms: float, payload: dict[str, Any]) -> None:
    trace = _ensure_trace(state)
    nodes = trace.get("nodes") or []
    end_ms = _ms()
    for i in range(len(nodes) - 1, -1, -1):
        n = nodes[i]
        if isinstance(n, dict) and n.get("name") == name and "end_ms" not in n:
            n["end_ms"] = end_ms
            n["latency_ms"] = float(end_ms) - float(start_ms)
            n["result"] = dict(payload)
            break
    trace["nodes"] = nodes


def _normalize_snippet(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _doc_trace_row(d: Any, *, snippet_chars: int) -> dict[str, Any]:
    meta = getattr(d, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
    expanded = str(meta.get("expanded_text") or "").strip()
    raw = expanded or str(getattr(d, "page_content", "") or "")
    snippet = _normalize_snippet(raw)[: max(0, int(snippet_chars))]
    return {
        "chunk_id": str(meta.get("chunk_id", "")),
        "source": str(meta.get("source", "")),
        "file_type": str(meta.get("file_type", "")),
        "parent_id": str(meta.get("parent_id", "")),
        "section_path": str(meta.get("section_path", "")),
        "page": meta.get("page"),
        "start_line": meta.get("start_line"),
        "end_line": meta.get("end_line"),
        "start_index": meta.get("start_index"),
        "rrf_score": meta.get("rrf_score"),
        "coarse_score": meta.get("coarse_score"),
        "rerank_score": meta.get("rerank_score"),
        "snippet": snippet,
    }


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


def _llm_appeal_failure(
    question: str,
    answer: str,
    failure_reason: dict[str, Any],
    evidence_set: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    LLM 申诉机制: 判断 gate 失败是否属于误判。
    
    返回:
        { "is_false_positive": bool, "reason": str, "suggested_fix": str | None }
    """
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
        # LLM 申诉失败时，保守起见，维持原失败判定
        return {"is_false_positive": False, "reason": "LLM appeal failed", "suggested_fix": None}


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
    
    # LLM 申诉机制：如果验证失败，让 LLM 判断是否为误判
    if failure_reason is not None:
        appeal_result = _llm_appeal_failure(
            question=state.get("question", ""),
            answer=answer,
            failure_reason=failure_reason,
            evidence_set=evidence_set,
        )
        
        # 如果 LLM 判定为误判，修正状态
        if appeal_result.get("is_false_positive", False):
            # 记录申诉成功，但保留原始失败信息用于审计
            failure_reason["appealed"] = True
            failure_reason["appeal_reason"] = appeal_result.get("reason", "")
            failure_reason["category"] = f"appealed_{failure_reason.get('category', 'unknown')}"
            # 修改为通过状态
            failure_reason = None  # 申诉成功，清除失败状态
        else:
            # 申诉失败，保留失败状态，并记录建议
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


def visualize_graph_mermaid() -> str:
    """
    生成 LangGraph 的 Mermaid 流程图.

    返回:
        Mermaid 格式的流程图字符串

    用途:
        - 可视化 agentic loop 的执行流程
        - 便于理解 nodes 和 edges 的关系
        - 可以在 Markdown 文档或 Mermaid 在线编辑器中查看
    """
    graph = build_langgraph_agentic_loop()
    try:
        return graph.get_graph().draw_mermaid()
    except Exception:
        return """
graph TD
    START([开始]) --> rewrite[查询改写]
    rewrite --> retrieve[检索与评估]
    retrieve --> |需要改进| revise[修订查询]
    retrieve --> |质量足够| decide_tool[决策工具调用]
    revise --> retrieve
    decide_tool --> |需要调用| call_tool[调用工具]
    decide_tool --> |不需要| synthesize[合成答案]
    call_tool --> synthesize
    synthesize --> validate[验证与落盘]
    validate --> END([结束])
"""


def build_langgraph_agentic_loop() -> Any:
    """Build LangGraph for agentic RAG loop."""
    try:
        from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("Missing optional dependency: langgraph") from e

    workflow = StateGraph(AgenticState)

    workflow.add_node("rewrite", node_rewrite)
    workflow.add_node("retrieve_and_critique", node_retrieve_and_critique)
    workflow.add_node("revise_query", node_revise_query)
    workflow.add_node("decide_tool_use", node_decide_tool_use)
    workflow.add_node("call_tool", node_call_tool)
    workflow.add_node("synthesize_answer", node_synthesize_answer)
    workflow.add_node("validate_and_save", node_validate_and_save)

    workflow.set_entry_point("rewrite")
    workflow.add_edge("rewrite", "retrieve_and_critique")
    workflow.add_conditional_edges(
        "retrieve_and_critique",
        should_continue_retrieval,
        {
            "revise_query": "revise_query",
            "decide_tool_use": "decide_tool_use",
        },
    )
    workflow.add_edge("revise_query", "retrieve_and_critique")
    workflow.add_conditional_edges(
        "decide_tool_use",
        should_call_tool,
        {
            "call_tool": "call_tool",
            "synthesize_answer": "synthesize_answer",
        },
    )
    workflow.add_edge("call_tool", "synthesize_answer")
    workflow.add_edge("synthesize_answer", "validate_and_save")
    workflow.add_edge("validate_and_save", END)

    return workflow.compile()


def run_langgraph_agentic_chat(
    question: str,
    retriever: Any,
    max_rounds: int = 2,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Run agentic chat using LangGraph orchestration.

    参数:
        question: 用户问题
        retriever: 检索器实例
        max_rounds: 最大重试轮数

    返回:
        与 run_agentic_chat 相同的输出 schema
    """
    graph = build_langgraph_agentic_loop()

    initial_state: AgenticState = {
        "question": question,
        "request_id": str(request_id or str(uuid.uuid4())),
        "run_id": str(uuid.uuid4()),
        "max_rounds": max_rounds,
        "retriever": retriever,
        "current_query": "",
        "improved_query": "",
        "current_round": 0,
        "docs": [],
        "critique_reason": "",
        "should_continue": False,
        "should_call_tool": False,
        "tool_args": {},
        "tool_reason": "",
        "tool_output": None,
        "tool_traces": [],
        "answer": "",
        "citations": [],
        "decision_log": [],
        "status": "ok",
        "failure_reason": None,
        "debug": {},
        "trace": {"nodes": [], "events": []},
    }

    final_state = graph.invoke(initial_state)

    return {
        "request_id": final_state.get("request_id", ""),
        "answer": final_state["answer"],
        "docs": final_state["docs"],
        "citations": final_state["citations"],
        "claims": final_state.get("claims", []),
        "evidence_set": final_state.get("evidence_set", []) or agentic_primitives.build_evidence_set_from_docs(
            final_state.get("docs", []),
            include_text=False,
        ),
        "decision_log": final_state["decision_log"],
        "tool_traces": final_state["tool_traces"],
        "status": final_state["status"],
        "failure_reason": final_state["failure_reason"],
        "debug": final_state["debug"],
    }
