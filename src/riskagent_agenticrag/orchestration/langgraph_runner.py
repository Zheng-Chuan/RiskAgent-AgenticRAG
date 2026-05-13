"""LangGraph 编排入口 -- 图构建, 运行, 可视化."""

from __future__ import annotations

import uuid
from typing import Any

from riskagent_agenticrag.orchestration.nodes import (
    node_retrieve_and_critique,
    node_revise_query,
    node_rewrite,
    node_synthesize_answer,
    node_validate_and_save,
    should_continue_retrieval,
)
from riskagent_agenticrag.orchestration.state import AgenticState
from riskagent_agenticrag.rag import agentic_primitives


def visualize_graph_mermaid() -> str:
    """生成 LangGraph 的 Mermaid 流程图."""
    graph = build_langgraph_agentic_loop()
    try:
        return graph.get_graph().draw_mermaid()
    except Exception:
        return """
graph TD
    START([开始]) --> rewrite[查询改写]
    rewrite --> retrieve[检索与评估]
    retrieve --> |需要改进| revise[修订查询]
    retrieve --> |质量足够| synthesize[合成答案]
    revise --> retrieve
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
    workflow.add_node("synthesize_answer", node_synthesize_answer)
    workflow.add_node("validate_and_save", node_validate_and_save)

    workflow.set_entry_point("rewrite")
    workflow.add_edge("rewrite", "retrieve_and_critique")
    workflow.add_conditional_edges(
        "retrieve_and_critique",
        should_continue_retrieval,
        {
            "revise_query": "revise_query",
            "synthesize_answer": "synthesize_answer",
        },
    )
    workflow.add_edge("revise_query", "retrieve_and_critique")
    workflow.add_edge("synthesize_answer", "validate_and_save")
    workflow.add_edge("validate_and_save", END)

    return workflow.compile()


def run_langgraph_agentic_chat(
    question: str,
    retriever: Any,
    max_rounds: int = 2,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Run agentic chat using LangGraph orchestration.

    Args:
        question: 用户问题
        retriever: 检索器实例
        max_rounds: 最大重试轮数
        request_id: 请求 ID (可选)

    Returns:
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
        "status": final_state["status"],
        "failure_reason": final_state["failure_reason"],
        "debug": final_state["debug"],
    }
