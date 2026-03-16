from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from riskagent_agenticrag.evaluation.advanced_metrics import (
    compute_retrieval_metrics,
    compute_gate_metrics,
    compute_reliability_cost_metrics,
)
from riskagent_agenticrag.evaluation.citation_precision import try_compute_citation_precision
from riskagent_agenticrag.evaluation.domain_consistency import try_compute_domain_consistency
from riskagent_agenticrag.evaluation.ragas_metrics import compute_all_ragas_metrics


@dataclass
class MetricModule:
    name: str
    description: str
    compute_fn: Callable
    required_keys: list[str]
    available_metrics: list[str]


METRIC_MODULES: dict[str, MetricModule] = {
    "domain_consistency": MetricModule(
        name="domain_consistency",
        description="领域一致性指标（数值、术语一致性）",
        compute_fn=try_compute_domain_consistency,
        required_keys=["answer", "contexts"],
        available_metrics=[
            "numeric_consistency_score",
            "glossary_consistency_score",
            "domain_consistency_score",
        ],
    ),
    "citation_precision": MetricModule(
        name="citation_precision",
        description="引用精度指标",
        compute_fn=try_compute_citation_precision,
        required_keys=["answer", "citations", "contexts"],
        available_metrics=[
            "citations_coverage",
            "citation_precision",
            "hallucination_rate_in_citations",
        ],
    ),
    "ragas": MetricModule(
        name="ragas",
        description="RAGAS 指标（全面的 RAG 质量评估）",
        compute_fn=compute_all_ragas_metrics,
        required_keys=["question", "answer", "contexts"],
        available_metrics=[
            "ragas_faithfulness",
            "ragas_answer_relevancy",
            "ragas_context_relevancy",
            "ragas_response_completeness",
            "ragas_context_precision_no_ref",
            "ragas_contradiction_score",
        ],
    ),
}


def _load_samples_from_report(report_path: Path) -> list[dict[str, Any]]:
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = data.get("samples", [])
    return samples


def compute_metrics(
    report_path: Path,
    module_name: str,
    metric_names: Optional[list[str]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    samples = _load_samples_from_report(report_path)
    module = METRIC_MODULES.get(module_name)
    if not module:
        available = list(METRIC_MODULES.keys())
        raise ValueError(f"Unknown metric module: {module_name}. Available: {available}")

    result: Any = None
    if module_name == "domain_consistency":
        tolerance = kwargs.get("tolerance", 0.1)
        result = module.compute_fn(samples=samples, tolerance=tolerance)
    elif module_name == "citation_precision":
        result = module.compute_fn(samples=samples)
    elif module_name == "ragas":
        include_ref = kwargs.get("include_reference_based", True)
        include_low = kwargs.get("include_low_priority", False)
        result = module.compute_fn(
            samples=samples,
            include_reference_based=include_ref,
            include_low_priority=include_low,
        )

    out: dict[str, Any] = {
        "module": module_name,
        "ok": getattr(result, "ok", True),
        "error": getattr(result, "error", None),
    }

    if hasattr(result, "metrics"):
        all_metrics = result.metrics
        if metric_names:
            filtered = {k: v for k, v in all_metrics.items() if k in metric_names}
            out["metrics"] = filtered
        else:
            out["metrics"] = all_metrics

    if hasattr(result, "details"):
        out["details"] = result.details

    return out


def main():
    parser = argparse.ArgumentParser(
        description="计算单一指标或指标模块",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=False,
        help="评估报告 JSON 路径 (e.g., .artifacts/reports/rag_eval_*.json)",
    )
    parser.add_argument(
        "--module",
        type=str,
        required=True,
        help="指标模块名称\n"
        "可用模块:\n"
        + "\n".join([f"  - {k}: {v.description}" for k, v in METRIC_MODULES.items()]),
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default=None,
        help="指定具体指标（逗号分隔），不指定则返回该模块所有指标\n"
        "e.g., --metrics numeric_consistency_score,glossary_consistency_score",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.1,
        help="数值一致性容差 (仅 domain_consistency 模块)",
    )
    parser.add_argument(
        "--include-reference-based",
        action="store_true",
        help="RAGAS: 包含需要 reference 的指标 (仅 ragas 模块)",
    )
    parser.add_argument(
        "--include-low-priority",
        action="store_true",
        help="RAGAS: 包含低优先级指标 (仅 ragas 模块)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出结果到指定文件 (JSON)",
    )
    parser.add_argument(
        "--list-metrics",
        action="store_true",
        help="列出指定模块的所有可用指标",
    )

    args = parser.parse_args()

    if args.list_metrics:
        mod = METRIC_MODULES.get(args.module)
        if not mod:
            available = list(METRIC_MODULES.keys())
            print(f"Unknown module: {args.module}")
            print(f"Available: {available}")
            return
        print(f"Module: {mod.name}")
        print(f"Description: {mod.description}")
        print(f"Available metrics:")
        for m in mod.available_metrics:
            print(f"  - {m}")
        return

    if not args.report:
        print("Error: --report is required (unless --list-metrics is used)")
        return

    if not args.report.exists():
        print(f"Error: Report file not found: {args.report}")
        return

    metric_names = None
    if args.metrics:
        metric_names = [s.strip() for s in args.metrics.split(",") if s.strip()]

    try:
        result = compute_metrics(
            report_path=args.report,
            module_name=args.module,
            metric_names=metric_names,
            tolerance=args.tolerance,
            include_reference_based=args.include_reference_based,
            include_low_priority=args.include_low_priority,
        )
    except Exception as e:
        print(f"Error computing metrics: {e}")
        import traceback

        traceback.print_exc()
        return

    print("=" * 70)
    print(f"Metrics: {args.module}")
    print("=" * 70)

    if not result.get("ok", True):
        print(f"❌ Error: {result.get('error')}")
        return

    print(f"✅ OK")
    print()

    metrics = result.get("metrics", {})
    if metrics:
        print("Metrics:")
        for k, v in sorted(metrics.items()):
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")
        print()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Output written to: {args.output}")

    print("=" * 70)


if __name__ == "__main__":
    main()
