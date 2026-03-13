"""Trace 工具 -- 节点级别的执行追踪记录."""

from __future__ import annotations

import time
from typing import Any

from riskagent_agenticrag.orchestration.state import AgenticState


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
