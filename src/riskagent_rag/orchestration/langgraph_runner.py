# 中文注释: LangGraph 编排层实现
# 用途: 将 agentic loop 的各个步骤用 LangGraph 重新编排, 统一 state 和 trace

from __future__ import annotations

import json
import uuid
from typing import Any, Literal, Optional, TypedDict

from langchain_core.documents import Document  # type: ignore[import-not-found]
from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

from riskagent_rag.agents.data_agent import run_data_agent
from riskagent_rag.artifacts.storage import save_artifact
from riskagent_rag.contracts.structured import StructuredRequest
from riskagent_rag.rag.pipeline import extract_citations
from riskagent_rag.validators.gates import validate_response
from riskagent_rag.rag.agentic_loop import (
    _attach_citations_to_each_paragraph,
    _critique_retrieval,
    _decide_tool_use,
    _rewrite_query,
    _synthesize_answer_with_tool,
    _utc_today_date,
)


class AgenticState(TypedDict, total=False):
    """LangGraph state schema for agentic RAG loop."""
    
    question: str
    max_rounds: int
    retriever: Any
    
    current_query: str
    current_round: int
    docs: list[Document]
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


def node_rewrite(state: AgenticState) -> AgenticState:
    """Node: rewrite query for better retrieval."""
    question = state["question"]
    rewritten = _rewrite_query(question)
    
    state["current_query"] = rewritten
    state["current_round"] = 0
    state["decision_log"] = state.get("decision_log", [])
    state["decision_log"].append({
        "step_id": "rewrite",
        "agent": "AgenticLoop",
        "rationale": "rewrite user question for retrieval",
        "chosen": rewritten,
        "alternatives": [question],
    })
    
    return state


def node_retrieve_and_critique(state: AgenticState) -> AgenticState:
    """Node: retrieve docs and critique quality."""
    retriever = state["retriever"]
    current_query = state["current_query"]
    question = state["question"]
    max_rounds = state["max_rounds"]
    current_round = state.get("current_round", 0)
    
    docs = retriever.invoke(current_query)
    
    sufficient, improved_query, critique_reason = _critique_retrieval(question, docs)
    
    should_continue = not sufficient and current_round < max_rounds
    
    state["docs"] = docs
    state["critique_reason"] = critique_reason
    state["should_continue"] = should_continue
    state["current_round"] = current_round + 1
    
    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": f"retrieve_round_{current_round}",
        "agent": "AgenticLoop",
        "rationale": critique_reason or "retrieval done",
        "chosen": "continue" if should_continue else "stop",
        "alternatives": [f"docs_count={len(docs)}"],
    })
    state["decision_log"] = decision_log
    
    return state


def node_revise_query(state: AgenticState) -> AgenticState:
    """Node: revise query based on critique."""
    question = state["question"]
    critique_reason = state["critique_reason"]
    current_query = state["current_query"]
    
    rewritten = _rewrite_query(f"{question}\n\nPrevious issue: {critique_reason}")
    state["current_query"] = rewritten
    
    decision_log = state.get("decision_log", [])
    decision_log.append({
        "step_id": "revise_query",
        "agent": "AgenticLoop",
        "rationale": "revise query based on critique",
        "chosen": rewritten,
        "alternatives": [current_query],
    })
    state["decision_log"] = decision_log
    
    return state


def node_decide_tool_use(state: AgenticState) -> AgenticState:
    """Node: decide whether to call tool."""
    question = state["question"]
    should_call, tool_args, tool_reason = _decide_tool_use(question)
    
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
    
    return state


def node_call_tool(state: AgenticState) -> AgenticState:
    """Node: call tool and collect traces."""
    question = state["question"]
    tool_args = state["tool_args"]
    
    desk = str(tool_args.get("desk", "")).strip()
    as_of = str(tool_args.get("as_of", "")).strip() or _utc_today_date()
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
    
    return state


def node_synthesize_answer(state: AgenticState) -> AgenticState:
    """Node: synthesize final answer with citations."""
    question = state["question"]
    docs = state["docs"]
    tool_output = state.get("tool_output")
    
    answer = _synthesize_answer_with_tool(question=question, docs=docs, tool_output=tool_output)
    citations = extract_citations(docs)
    answer_with_citations = _attach_citations_to_each_paragraph(answer, citations)
    
    state["answer"] = answer_with_citations
    state["citations"] = citations
    
    return state


def node_validate_and_save(state: AgenticState) -> AgenticState:
    """Node: validate response and save artifact."""
    answer = state["answer"]
    docs = state["docs"]
    tool_traces = state.get("tool_traces", [])
    tool_output = state.get("tool_output")
    
    claims: list[dict[str, Any]] = []
    evidence_set: list[dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        evidence_id = f"ev_{idx}"
        start_index_raw = doc.metadata.get("start_index", 0)
        try:
            start_index = int(start_index_raw)
        except Exception:
            start_index = 0
        evidence_set.append({
            "evidence_id": evidence_id,
            "source": doc.metadata.get("source", ""),
            "chunk_id": doc.metadata.get("chunk_id", ""),
            "start_index": start_index,
            "snippet": (doc.page_content or "")[:200],
            "text": doc.page_content[:200],
        })
    
    failure_reason = validate_response(
        report=answer,
        claims=claims,
        evidence_set=evidence_set,
        tool_traces=tool_traces,
        docs=docs,
    )
    
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
    
    request_id = str(uuid.uuid4())
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

    structured_evidence_set: list[dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        evidence_id = f"ev_{idx}"
        start_index_raw = doc.metadata.get("start_index", 0)
        try:
            start_index = int(start_index_raw)
        except Exception:
            start_index = 0
        structured_evidence_set.append(
            {
                "evidence_id": evidence_id,
                "source": str(doc.metadata.get("source", "")),
                "chunk_id": str(doc.metadata.get("chunk_id", "")),
                "start_index": start_index,
                "snippet": (doc.page_content or "")[:200],
            }
        )

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
        artifact_path = save_artifact(
            request_id,
            request_data,
            response_data,
            structured_response_data=structured_payload,
        )
        debug_info["artifact_path"] = artifact_path
    except Exception as e:
        debug_info["artifact_error"] = str(e)
    
    state["debug"] = debug_info
    
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
        "max_rounds": max_rounds,
        "retriever": retriever,
        "current_query": "",
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
    }
    
    final_state = graph.invoke(initial_state)
    
    return {
        "answer": final_state["answer"],
        "docs": final_state["docs"],
        "citations": final_state["citations"],
        "decision_log": final_state["decision_log"],
        "tool_traces": final_state["tool_traces"],
        "status": final_state["status"],
        "failure_reason": final_state["failure_reason"],
        "debug": final_state["debug"],
    }
