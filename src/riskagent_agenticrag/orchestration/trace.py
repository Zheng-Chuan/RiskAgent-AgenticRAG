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


def _trace_node_end(
    state: AgenticState,
    name: str,
    start_ms: float,
    payload: dict[str, Any],
    token_usage: dict[str, int] | None = None,
) -> None:
    trace = _ensure_trace(state)
    nodes = trace.get("nodes") or []
    end_ms = _ms()
    for i in range(len(nodes) - 1, -1, -1):
        n = nodes[i]
        if isinstance(n, dict) and n.get("name") == name and "end_ms" not in n:
            n["end_ms"] = end_ms
            n["latency_ms"] = float(end_ms) - float(start_ms)
            n["result"] = dict(payload)
            # 写入 token 用量统计
            if token_usage is not None:
                n["token_usage"] = dict(token_usage)
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


# ---------------------------------------------------------------------------
# 检索诊断埋点
# ---------------------------------------------------------------------------

def _trace_retrieval_diag(state: AgenticState, debug_stats: dict[str, Any]) -> None:
    """从 retriever.debug_stats 中提取检索诊断信息写入 trace.

    参数:
        state: AgenticState, trace 信息写入 state["trace"]
        debug_stats: 检索器 debug_stats() 返回的字典
    """
    trace = _ensure_trace(state)
    diag: dict[str, Any] = {}

    try:
        # ---- dense search ----
        diag["dense"] = {
            "count": int(debug_stats.get("dense_count", debug_stats.get("dense_k", 0))),
            "latency_ms": debug_stats.get("dense_latency_ms"),
            "top1_score": debug_stats.get("dense_top1_score"),
        }

        # ---- sparse search ----
        diag["sparse"] = {
            "count": int(debug_stats.get("sparse_count", debug_stats.get("sparse_k", 0))),
            "latency_ms": debug_stats.get("sparse_latency_ms"),
        }

        # ---- rerank ----
        diag["rerank"] = {
            "input_count": int(debug_stats.get("rerank_input_count", debug_stats.get("rerank_k", 0))),
            "output_count": int(debug_stats.get("rerank_output_count", debug_stats.get("rerank_k", 0))),
            "latency_ms": debug_stats.get("rerank_latency_ms"),
        }

        # ---- MMR diversity ----
        diag["mmr"] = {
            "before_count": debug_stats.get("mmr_before_count"),
            "after_count": debug_stats.get("mmr_after_count"),
        }

        # ---- 其他配置信息 ----
        # reranker_model 语义: 实际生效的模型 (active 优先, 回退请求名);
        # 单纯的环境变量请求名在远程 fallback 场景下会误导排障.
        active_model = str(debug_stats.get("active_reranker_model") or "").strip()
        requested_model = str(debug_stats.get("reranker_model") or "").strip()
        diag["config"] = {
            "dense_k": debug_stats.get("dense_k"),
            "sparse_k": debug_stats.get("sparse_k"),
            "candidate_k": debug_stats.get("candidate_k"),
            "rerank_k": debug_stats.get("rerank_k"),
            "final_k": debug_stats.get("final_k"),
            "rrf_k": debug_stats.get("rrf_k"),
            "reranker_model": active_model or requested_model,
            "reranker_status": debug_stats.get("reranker_status"),
            "has_bm25": debug_stats.get("has_bm25"),
        }
    except Exception:
        diag = {"fallback": str(debug_stats)[:500]}

    trace["retrieval_diag"] = diag
