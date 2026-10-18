from __future__ import annotations

import json
from typing import Any


def _to_float(v: Any, fallback: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback


def load_thresholds(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    try:
        import yaml  # type: ignore[import-not-found]

        obj = yaml.safe_load(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    raise ValueError(f"Cannot parse thresholds file: {path}")


def _ci_bound(entry: Any, key: str, fallback: float | None) -> float | None:
    """从 CI 条目取边界值, 无效或缺失时返回 fallback."""
    if not isinstance(entry, dict):
        return fallback
    try:
        return float(entry.get(key))
    except (TypeError, ValueError):
        return fallback


def evaluate_threshold_gate(
    *,
    report: dict[str, Any],
    baseline_diff: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}

    defaults = config.get("default")
    if not isinstance(defaults, dict):
        defaults = {}
    metric_rules = config.get("metrics")
    if not isinstance(metric_rules, dict):
        metric_rules = {}

    fail_on_regression = bool(config.get("fail_on_regression", True))

    # CI 口径 (RFC-006 A2): 有置信区间的指标, 阈值判定用保守边界
    # (higher_is_better 用 ci_low, lower_is_better 用 ci_high), 报告可配置关闭.
    use_ci = bool(config.get("use_confidence_intervals", True))
    ci_section = report.get("confidence_intervals")
    ci_metrics: dict[str, Any] = {}
    if use_ci and isinstance(ci_section, dict):
        raw_ci = ci_section.get("metrics")
        if isinstance(raw_ci, dict):
            ci_metrics = raw_ci

    failures: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for name, rule in metric_rules.items():
        if not isinstance(rule, dict):
            continue
        if name not in metrics:
            warnings.append({"metric": name, "reason": "missing_metric"})
            continue

        current = _to_float(metrics.get(name), 0.0)
        direction = str(rule.get("direction", "")).strip().lower()

        minimum = _to_float(rule.get("minimum", defaults.get("minimum")), float("-inf"))
        maximum = _to_float(rule.get("maximum", defaults.get("maximum")), float("inf"))
        tolerance = abs(_to_float(rule.get("tolerance", defaults.get("tolerance", 0.0)), 0.0))

        check_min = minimum != float("-inf")
        check_max = maximum != float("inf")
        if direction == "higher_is_better":
            check_max = False
        if direction == "lower_is_better":
            check_min = False

        ci_entry = ci_metrics.get(name) if name in ci_metrics else None

        if check_min and check_max:
            # 双侧检查: min 用下界, max 用上界
            min_current = _ci_bound(ci_entry, "ci_low", current)
            max_current = _ci_bound(ci_entry, "ci_high", current)
        elif check_min:
            min_current = _ci_bound(ci_entry, "ci_low", current)
            max_current = current
        else:
            min_current = current
            max_current = _ci_bound(ci_entry, "ci_high", current)

        if check_min and min_current < (minimum - tolerance):
            failures.append(
                {
                    "metric": name,
                    "reason": "below_minimum",
                    "current": current,
                    "minimum": minimum,
                    "tolerance": tolerance,
                    "ci_low": _ci_bound(ci_entry, "ci_low", None),
                    "judged_value": min_current,
                }
            )
        if check_max and max_current > (maximum + tolerance):
            failures.append(
                {
                    "metric": name,
                    "reason": "above_maximum",
                    "current": current,
                    "maximum": maximum,
                    "tolerance": tolerance,
                    "ci_high": _ci_bound(ci_entry, "ci_high", None),
                    "judged_value": max_current,
                }
            )

    baseline_comparisons = baseline_diff
    if isinstance(baseline_diff, dict) and isinstance(baseline_diff.get("comparisons"), dict):
        baseline_comparisons = baseline_diff.get("comparisons")

    if fail_on_regression and isinstance(baseline_comparisons, dict):
        for name, payload in baseline_comparisons.items():
            if not isinstance(payload, dict):
                continue
            if bool(payload.get("baseline_regression", payload.get("regression", False))):
                regressions.append(
                    {
                        "metric": str(name),
                        "reason": "baseline_regression",
                        "delta": payload.get("delta"),
                        "current": payload.get("current"),
                        "baseline": payload.get("baseline"),
                    }
                )

    verdict = "pass"
    if failures or regressions:
        verdict = "fail"
    elif warnings:
        verdict = "warning"

    return {
        "verdict": verdict,
        "failures": failures,
        "regressions": regressions,
        "warnings": warnings,
        "checked_metrics": sorted([k for k, v in metric_rules.items() if isinstance(v, dict)]),
        "fail_on_regression": fail_on_regression,
        "use_confidence_intervals": use_ci,
        "confidence_interval_metrics": sorted(ci_metrics.keys()),
    }
