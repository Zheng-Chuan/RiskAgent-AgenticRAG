"""Evaluation reporting.

中文注释
- 评测报告落盘
- 读取上一份报告对比标记退化
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _sanitize_label(label: str) -> str:
    out: list[str] = []
    for ch in label.strip():
        if ch.isalnum() or ch in ("-", "_"):
            out.append(ch.lower())
        elif ch.isspace():
            out.append("_")
    return "".join(out).strip("_")


def ensure_reports_dir(*, artifacts_dir: str = ".artifacts") -> Path:
    base = Path(artifacts_dir)
    base.mkdir(parents=True, exist_ok=True)
    reports_dir = base / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def write_report(report: dict[str, Any], *, artifacts_dir: str = ".artifacts", label: str = "") -> str:
    reports_dir = ensure_reports_dir(artifacts_dir=artifacts_dir)
    safe_label = _sanitize_label(label) if label else ""
    filename = f"rag_eval_{safe_label + '_' if safe_label else ''}{_utc_timestamp()}.json"
    path = reports_dir / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def list_reports(*, artifacts_dir: str = ".artifacts") -> list[Path]:
    reports_dir = ensure_reports_dir(artifacts_dir=artifacts_dir)
    paths = sorted(reports_dir.glob("rag_eval_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return paths


def load_report(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_latest_report(*, artifacts_dir: str = ".artifacts") -> Optional[str]:
    paths = list_reports(artifacts_dir=artifacts_dir)
    if not paths:
        return None
    return str(paths[0])


@dataclass(frozen=True)
class RegressionCheck:
    baseline_regression: bool
    threshold_failure: bool
    delta: float
    current: float
    baseline: float


def _compare_metric(
    *,
    current: float,
    baseline: float,
    tolerance: float,
    minimum: float | None = None,
    maximum: float | None = None,
    lower_is_better: bool = False,
) -> RegressionCheck:
    delta = current - baseline
    if lower_is_better:
        threshold_failure = current > maximum if maximum is not None else False
        baseline_regression = delta > abs(tolerance)
    else:
        threshold_failure = current < minimum if minimum is not None else False
        baseline_regression = delta < -abs(tolerance)
    return RegressionCheck(
        baseline_regression=baseline_regression,
        threshold_failure=threshold_failure,
        delta=delta,
        current=current,
        baseline=baseline,
    )


def compare_reports(
    *,
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
    tolerance: float = 0.0,
    minimum: float = 0.0,
    hallucination_maximum: float = 1.0,
) -> dict[str, Any]:
    current_metrics = current_report.get("metrics")
    baseline_metrics = baseline_report.get("metrics")
    if not isinstance(current_metrics, dict):
        current_metrics = {}
    if not isinstance(baseline_metrics, dict):
        baseline_metrics = {}

    higher_better_explicit = {
        "citations_coverage",
        "citation_precision",
        "numeric_consistency_score",
        "glossary_consistency_score",
        "domain_consistency_score",
        "retrieval_mrr",
        "retrieval_dense_hit_rate",
        "retrieval_sparse_hit_rate",
        "retrieval_hybrid_gain_rate",
        "retrieval_rerank_uplift",
        "gate_block_benefit_rate",
        "reliability_success_rate",
        "ragas_faithfulness",
        "ragas_answer_relevancy",
        "ragas_context_relevancy",
        "ragas_context_precision_no_ref",
        "ragas_context_recall",
        "ragas_answer_correctness",
        "ragas_response_completeness",
    }
    lower_better_explicit = {
        "hallucination_rate_in_citations",
        "gate_false_kill_rate",
        "reliability_error_rate",
        "reliability_timeout_rate",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "cost_estimated_usd",
        "ragas_contradiction_score",
    }
    out: dict[str, Any] = {}
    baseline_regression_metrics: list[str] = []
    threshold_failure_metrics: list[str] = []

    common_metrics = sorted(set(current_metrics.keys()).intersection(set(baseline_metrics.keys())))
    for metric in common_metrics:
        try:
            curr = float(current_metrics.get(metric, 0.0))
            base = float(baseline_metrics.get(metric, 0.0))
        except (TypeError, ValueError):
            continue

        is_lower_better = metric in lower_better_explicit or metric.endswith("_rate")
        if metric in higher_better_explicit:
            is_lower_better = False
        if metric.startswith("retrieval_recall_at_") or metric.startswith("retrieval_ndcg_at_"):
            is_lower_better = False

        if is_lower_better:
            maximum = hallucination_maximum if metric == "hallucination_rate_in_citations" else float("inf")
            check = _compare_metric(
                current=curr,
                baseline=base,
                tolerance=tolerance,
                maximum=maximum,
                lower_is_better=True,
            )
            payload: dict[str, Any] = {
                "current": check.current,
                "baseline": check.baseline,
                "delta": check.delta,
                "baseline_regression": check.baseline_regression,
                "threshold_failure": check.threshold_failure,
                "regression": bool(check.baseline_regression or check.threshold_failure),
                "tolerance": tolerance,
            }
            if metric == "hallucination_rate_in_citations":
                payload["maximum"] = hallucination_maximum
            out[metric] = payload
            if check.baseline_regression:
                baseline_regression_metrics.append(metric)
            if check.threshold_failure:
                threshold_failure_metrics.append(metric)
            continue

        check = _compare_metric(
            current=curr,
            baseline=base,
            tolerance=tolerance,
            minimum=minimum,
        )
        out[metric] = {
            "current": check.current,
            "baseline": check.baseline,
            "delta": check.delta,
            "baseline_regression": check.baseline_regression,
            "threshold_failure": check.threshold_failure,
            "regression": bool(check.baseline_regression or check.threshold_failure),
            "tolerance": tolerance,
            "minimum": minimum,
        }
        if check.baseline_regression:
            baseline_regression_metrics.append(metric)
        if check.threshold_failure:
            threshold_failure_metrics.append(metric)
    return {
        "comparisons": out,
        "summary": {
            "baseline_regression_metrics": sorted(baseline_regression_metrics),
            "threshold_failure_metrics": sorted(threshold_failure_metrics),
        },
    }
