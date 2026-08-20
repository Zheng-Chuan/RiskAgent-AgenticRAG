"""Agentic RAG state schema -- LangGraph 状态定义."""

from __future__ import annotations

from typing import Any, Optional, TypedDict


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
    # SEAL-RAG (FR-12): 固定容量证据集, 跨轮次保留高分证据并替换最弱的
    evidence_budget: Any
    # TARG (FR-11): 查询复杂性评估结果与是否跳过 fanout 的标记
    query_complexity: dict[str, Any]
    skip_fanout: bool

    answer: str
    citations: list[dict[str, str]]
    claims: list[dict[str, Any]]
    evidence_set: list[dict[str, Any]]
    tool_traces: list[dict[str, Any]]
    decision_log: list[dict[str, Any]]

    status: str
    failure_reason: Optional[dict[str, Any]]
    debug: dict[str, Any]
