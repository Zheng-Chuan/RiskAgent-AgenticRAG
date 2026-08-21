"""延迟分位数统计 -- 扫描所有 trace 文件, 按节点/查询类型统计延迟."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---- 工具函数 ----

def _percentile(values: list[float], p: float) -> float:
    """计算百分位数值 (线性插值)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[-1]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def _load_traces(artifacts_dir: str | None = None) -> list[dict[str, Any]]:
    """加载所有 trace 文件."""
    if artifacts_dir is None:
        artifacts_dir = os.getenv("RISKAGENT_ARTIFACTS_DIR", ".artifacts").strip()
    traces_dir = Path(artifacts_dir) / "traces"
    if not traces_dir.is_dir():
        return []

    traces: list[dict[str, Any]] = []
    for f in traces_dir.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            traces.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return traces


def _extract_query_type(trace: dict[str, Any]) -> str:
    """从 trace 中提取查询类型.

    优先从 self_rag 数据中获取 question_type,
    否则从 retrieval_diag 的 config 中推断.
    """
    # 尝试从 nodes 中查找 self_rag 的 question_type
    for node in trace.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        result = node.get("result", {})
        if isinstance(result, dict):
            docs = result.get("docs", [])
            if isinstance(docs, list):
                for doc in docs:
                    if isinstance(doc, dict):
                        grade = doc.get("grade")
                        if isinstance(grade, dict):
                            qt = grade.get("question_type")
                            if qt:
                                return str(qt)

    # 从 retrieval_diag 中推断
    diag = trace.get("retrieval_diag", {})
    if isinstance(diag, dict):
        config = diag.get("config", {})
        if isinstance(config, dict):
            # 使用 reranker_model 作为粗略分类
            model = config.get("reranker_model")
            if model:
                return f"reranker={model}"

    return "unknown"


def collect_latency_stats(artifacts_dir: str | None = None) -> dict[str, Any]:
    """扫描所有 trace 文件, 按节点名称和查询类型统计 p50/p95/p99 延迟.

    参数:
        artifacts_dir: 存储根目录, 默认从环境变量 RISKAGENT_ARTIFACTS_DIR 读取

    返回:
        {
            "total_traces": int,
            "by_node": {
                "node_name": {
                    "count": int,
                    "p50_ms": float,
                    "p95_ms": float,
                    "p99_ms": float,
                    "avg_ms": float,
                    "min_ms": float,
                    "max_ms": float,
                },
                ...
            },
            "by_query_type": {
                "query_type": {
                    "count": int,
                    "total_latency": {
                        "p50_ms": float,
                        "p95_ms": float,
                        "p99_ms": float,
                        "avg_ms": float,
                    },
                    "by_node": {
                        "node_name": {
                            "p50_ms": float,
                            "p95_ms": float,
                            "p99_ms": float,
                            "avg_ms": float,
                            "count": int,
                        },
                        ...
                    },
                },
                ...
            },
        }
    """
    traces = _load_traces(artifacts_dir)

    # 按节点名称收集延迟
    node_latency_map: dict[str, list[float]] = {}
    # 按查询类型 + 节点名称收集延迟
    type_node_latency_map: dict[str, dict[str, list[float]]] = {}
    # 按查询类型收集端到端延迟
    type_total_latency_map: dict[str, list[float]] = {}

    for trace in traces:
        query_type = _extract_query_type(trace)
        type_node_latency_map.setdefault(query_type, {})
        total_latency = 0.0

        for node in trace.get("nodes", []) or []:
            if not isinstance(node, dict):
                continue
            name = node.get("name", "?")
            latency = node.get("latency_ms")
            if latency is None:
                continue

            latency_f = float(latency)
            total_latency += latency_f

            # 按节点统计
            node_latency_map.setdefault(name, []).append(latency_f)

            # 按查询类型 + 节点统计
            type_node_latency_map[query_type].setdefault(name, []).append(latency_f)

        type_total_latency_map.setdefault(query_type, []).append(total_latency)

    # 构建 by_node 统计
    def _node_stats(lats: list[float]) -> dict[str, Any]:
        if not lats:
            return {
                "count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0,
            }
        return {
            "count": len(lats),
            "p50_ms": round(_percentile(lats, 50), 2),
            "p95_ms": round(_percentile(lats, 95), 2),
            "p99_ms": round(_percentile(lats, 99), 2),
            "avg_ms": round(sum(lats) / len(lats), 2),
            "min_ms": round(min(lats), 2),
            "max_ms": round(max(lats), 2),
        }

    by_node: dict[str, Any] = {}
    for name, lats in sorted(node_latency_map.items()):
        by_node[name] = _node_stats(lats)

    # 构建 by_query_type 统计
    by_query_type: dict[str, Any] = {}
    for qtype, node_map in sorted(type_node_latency_map.items()):
        total_lats = type_total_latency_map.get(qtype, [])
        by_node_for_type: dict[str, Any] = {}
        for name, lats in sorted(node_map.items()):
            by_node_for_type[name] = _node_stats(lats)

        by_query_type[qtype] = {
            "count": len(total_lats),
            "total_latency": _node_stats(total_lats),
            "by_node": by_node_for_type,
        }

    return {
        "total_traces": len(traces),
        "by_node": by_node,
        "by_query_type": by_query_type,
    }
