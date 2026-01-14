"""Evaluation reporting.

中文注释
- 评测报告落盘
- 读取上一份报告对比标记退化
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def _utc_timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_reports_dir(*, artifacts_dir: str = ".artifacts") -> Path:
    base = Path(artifacts_dir)
    base.mkdir(parents=True, exist_ok=True)
    reports_dir = base / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def write_report(report: dict[str, Any], *, artifacts_dir: str = ".artifacts") -> str:
    reports_dir = ensure_reports_dir(artifacts_dir=artifacts_dir)
    filename = f"rag_eval_{_utc_timestamp()}.json"
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
    regression: bool
    delta: float
    current: float
    baseline: float


def compare_metric_higher_is_better(
    *,
    current: float,
    baseline: float,
    tolerance: float,
    minimum: float,
) -> RegressionCheck:
    delta = current - baseline
    regression = current < minimum or delta < -abs(tolerance)
    return RegressionCheck(
        regression=regression,
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
) -> dict[str, Any]:
    current_metrics = current_report.get("metrics")
    baseline_metrics = baseline_report.get("metrics")
    if not isinstance(current_metrics, dict):
        current_metrics = {}
    if not isinstance(baseline_metrics, dict):
        baseline_metrics = {}

    current_cov = float(current_metrics.get("citations_coverage", 0.0))
    baseline_cov = float(baseline_metrics.get("citations_coverage", 0.0))

    check = compare_metric_higher_is_better(
        current=current_cov,
        baseline=baseline_cov,
        tolerance=tolerance,
        minimum=minimum,
    )

    return {
        "citations_coverage": {
            "current": check.current,
            "baseline": check.baseline,
            "delta": check.delta,
            "regression": check.regression,
            "tolerance": tolerance,
            "minimum": minimum,
        }
    }
