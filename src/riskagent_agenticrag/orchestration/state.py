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

    answer: str
    citations: list[dict[str, str]]
    claims: list[dict[str, Any]]
    evidence_set: list[dict[str, Any]]
    tool_traces: list[dict[str, Any]]
    decision_log: list[dict[str, Any]]

    status: str
    failure_reason: Optional[dict[str, Any]]
    debug: dict[str, Any]
