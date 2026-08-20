#!/usr/bin/env python3
"""Trace 检查 CLI 工具 -- 查询, 列出, 统计 trace 文件.

用法:
  python scripts/trace_inspect.py --trace-id <trace_id>
  python scripts/trace_inspect.py --last 10
  python scripts/trace_inspect.py --stats
  python scripts/trace_inspect.py --trace-id <trace_id> --stats
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


# ---- 工具函数 ----

def _traces_dir() -> Path:
    """获取 trace 文件存储目录."""
    artifacts_dir = os.getenv("RISKAGENT_ARTIFACTS_DIR", ".artifacts").strip()
    return Path(artifacts_dir) / "traces"


def _load_all_traces() -> list[tuple[Path, dict[str, Any]]]:
    """加载所有 trace 文件, 按修改时间倒序排列."""
    traces_dir = _traces_dir()
    if not traces_dir.is_dir():
        return []

    results: list[tuple[Path, dict[str, Any]]] = []
    for f in sorted(traces_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            results.append((f, data))
        except (json.JSONDecodeError, OSError):
            pass
    return results


def _load_trace(trace_id: str) -> dict[str, Any] | None:
    """按 trace_id 加载单个 trace 文件."""
    traces_dir = _traces_dir()
    trace_file = traces_dir / f"{trace_id}.json"
    if not trace_file.is_file():
        return None
    try:
        with open(trace_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _format_ms(ms: float | None) -> str:
    """格式化毫秒值."""
    if ms is None:
        return "N/A"
    return f"{float(ms):.1f}ms"


def _format_tokens(tu: dict[str, int] | None) -> str:
    """格式化 token 用量."""
    if not tu:
        return "N/A"
    p = int(tu.get("prompt_tokens", 0))
    c = int(tu.get("completion_tokens", 0))
    return f"p={p} c={c} (total={p + c})"


# ---- trace 详细查询 ----

def cmd_inspect_trace(trace_id: str) -> None:
    """查询指定 trace 的完整链路."""
    trace = _load_trace(trace_id)
    if trace is None:
        print(f"错误: 未找到 trace: {trace_id}")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print(f"Trace 详情: {trace_id}")
    print(f"{'=' * 80}")

    # 基本信息
    print(f"\n 模型:        {trace.get('model_id', 'N/A')}")
    print(f"  Prompt 版本:  {trace.get('prompt_version', 'N/A')}")
    print(f"  保存时间:      {trace.get('_saved_at', 'N/A')}")

    # 最终结果
    final = trace.get("final", {})
    if final:
        print(f"\n  最终状态:  {final.get('status', 'N/A')}")
        if final.get("failure_reason"):
            fr = final["failure_reason"]
            print(f"  失败原因:  {fr.get('category', 'N/A')} - {fr.get('message', 'N/A')}")

    # 节点执行链路
    nodes = trace.get("nodes", []) or []
    print(f"\n{'─' * 80}")
    print(f"  节点执行链路 ({len(nodes)} 个节点)")
    print(f"{'─' * 80}")

    # 表头
    header = f"  {'节点':<28} {'延迟':>10} {'Token 用量':>30} {'状态':>10}"
    print(header)
    print(f"  {'─' * 28} {'─' * 10} {'─' * 30} {'─' * 10}")

    total_latency = 0.0
    total_prompt = 0
    total_completion = 0

    for node in nodes:
        name = node.get("name", "?")
        latency = node.get("latency_ms")
        tu = node.get("token_usage")
        result = node.get("result", {})

        if latency is not None:
            total_latency += float(latency)

        if isinstance(tu, dict):
            total_prompt += int(tu.get("prompt_tokens", 0))
            total_completion += int(tu.get("completion_tokens", 0))

        status = "OK"
        if isinstance(result, dict):
            st = result.get("status") or result.get("should_continue")
            if st is not None:
                status = str(st)[:10]

        print(f"  {name:<28} {_format_ms(latency):>10} {_format_tokens(tu):>30} {status:>10}")

    # 汇总
    print(f"  {'─' * 28} {'─' * 10} {'─' * 30} {'─' * 10}")
    total_tokens = f"p={total_prompt} c={total_completion} (total={total_prompt + total_completion})"
    print(f"  {'总计':<28} {_format_ms(total_latency):>10} {total_tokens:>30}")

    # 检索诊断
    diag = trace.get("retrieval_diag")
    if diag:
        print(f"\n{'─' * 80}")
        print(f"  检索诊断")
        print(f"{'─' * 80}")

        dense = diag.get("dense", {})
        if dense:
            print(f"  Dense 检索:    count={dense.get('count')}, latency={_format_ms(dense.get('latency_ms'))}, top1_score={dense.get('top1_score')}")

        sparse = diag.get("sparse", {})
        if sparse:
            print(f"  Sparse 检索:   count={sparse.get('count')}, latency={_format_ms(sparse.get('latency_ms'))}")

        rerank = diag.get("rerank", {})
        if rerank:
            print(f"  Rerank:        input={rerank.get('input_count')}, output={rerank.get('output_count')}, latency={_format_ms(rerank.get('latency_ms'))}")

        mmr = diag.get("mmr", {})
        if mmr:
            print(f"  MMR Diversity: before={mmr.get('before_count')}, after={mmr.get('after_count')}")

    print(f"\n{'=' * 80}\n")


# ---- 最近 N 个 trace 摘要 ----

def cmd_list_traces(n: int) -> None:
    """列出最近 N 个 trace 的摘要."""
    traces = _load_all_traces()
    if not traces:
        print("未找到任何 trace 文件.")
        return

    traces = traces[:n]

    print(f"\n{'=' * 80}")
    print(f"最近 {len(traces)} 个 Trace 摘要")
    print(f"{'=' * 80}")

    header = f"  {'Trace ID':<42} {'节点数':>6} {'延迟':>10} {'Token':>25} {'状态':>8}"
    print(header)
    print(f"  {'─' * 42} {'─' * 6} {'─' * 10} {'─' * 25} {'─' * 8}")

    for f, trace in traces:
        trace_id = trace.get("_trace_id", f.stem)[:42]
        nodes = trace.get("nodes", []) or []

        total_latency = sum(float(n.get("latency_ms", 0)) for n in nodes if isinstance(n, dict))
        total_p = sum(int((n.get("token_usage") or {}).get("prompt_tokens", 0)) for n in nodes if isinstance(n, dict))
        total_c = sum(int((n.get("token_usage") or {}).get("completion_tokens", 0)) for n in nodes if isinstance(n, dict))

        final = trace.get("final", {})
        status = str(final.get("status", "?"))[:8]

        tokens = f"p={total_p} c={total_c}"
        print(f"  {trace_id:<42} {len(nodes):>6} {_format_ms(total_latency):>10} {tokens:>25} {status:>8}")

    print(f"{'=' * 80}\n")


# ---- 延迟统计 ----

def _percentile(values: list[float], p: float) -> float:
    """计算百分位数值."""
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


def cmd_stats() -> None:
    """按节点统计延迟 p50/p95/p99."""
    traces = _load_all_traces()
    if not traces:
        print("未找到任何 trace 文件.")
        return

    # 按节点名称收集延迟
    node_latencies: dict[str, list[float]] = {}
    for _, trace in traces:
        for node in trace.get("nodes", []) or []:
            if not isinstance(node, dict):
                continue
            name = node.get("name", "?")
            latency = node.get("latency_ms")
            if latency is not None:
                node_latencies.setdefault(name, []).append(float(latency))

    print(f"\n{'=' * 80}")
    print(f"节点延迟统计 (共 {len(traces)} 个 trace)")
    print(f"{'=' * 80}")

    header = f"  {'节点':<28} {'样本数':>8} {'p50':>10} {'p95':>10} {'p99':>10} {'avg':>10}"
    print(header)
    print(f"  {'─' * 28} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10}")

    total_latencies: list[float] = []
    for name in sorted(node_latencies.keys()):
        lats = node_latencies[name]
        total_latencies.extend(lats)
        avg = sum(lats) / len(lats) if lats else 0.0
        print(
            f"  {name:<28} {len(lats):>8} "
            f"{_format_ms(_percentile(lats, 50)):>10} "
            f"{_format_ms(_percentile(lats, 95)):>10} "
            f"{_format_ms(_percentile(lats, 99)):>10} "
            f"{_format_ms(avg):>10}"
        )

    # 总计
    if total_latencies:
        avg = sum(total_latencies) / len(total_latencies)
        print(f"  {'─' * 28} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10}")
        print(
            f"  {'总计(端到端)':<28} {len(total_latencies):>8} "
            f"{_format_ms(_percentile(total_latencies, 50)):>10} "
            f"{_format_ms(_percentile(total_latencies, 95)):>10} "
            f"{_format_ms(_percentile(total_latencies, 99)):>10} "
            f"{_format_ms(avg):>10}"
        )

    print(f"{'=' * 80}\n")


# ---- 主入口 ----

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace 检查 CLI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --trace-id abc123
  %(prog)s --last 10
  %(prog)s --stats
  %(prog)s --trace-id abc123 --stats
        """,
    )
    parser.add_argument("--trace-id", type=str, help="查询指定 trace 的完整链路")
    parser.add_argument("--last", type=int, help="列出最近 N 个 trace 的摘要")
    parser.add_argument("--stats", action="store_true", help="按节点统计延迟 p50/p95/p99")

    args = parser.parse_args()

    if not any([args.trace_id, args.last, args.stats]):
        parser.print_help()
        sys.exit(1)

    if args.trace_id:
        cmd_inspect_trace(args.trace_id)

    if args.last:
        cmd_list_traces(args.last)

    if args.stats:
        cmd_stats()


if __name__ == "__main__":
    main()