"""Evaluation Report Generator - Markdown Format.

生成格式清晰的 Markdown 评估报告.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class EvaluationSummary:
    """评估摘要数据."""
    timestamp: str
    total_samples: int
    passed_samples: int
    failed_samples: int
    metrics: dict[str, float]
    ragas_metrics: dict[str, float]
    category_scores: dict[str, dict[str, float]]


def generate_markdown_report(
    *,
    report_data: dict[str, Any],
    output_path: Path,
    title: str = "RAG Evaluation Report",
    include_raw_scores: bool = False,
) -> Path:
    """生成 Markdown 格式的评估报告.
    
    Args:
        report_data: 评估结果数据
        output_path: 输出文件路径
        title: 报告标题
        include_raw_scores: 是否包含原始分数（每样本）
    
    Returns:
        生成的报告文件路径
    """
    lines = []
    
    # 标题
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 执行摘要
    lines.append("## Executive Summary")
    lines.append("")
    
    samples = report_data.get("samples", [])
    total = len(samples)
    passed = sum(1 for s in samples if s.get("passed", False))
    failed = total - passed
    
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Samples | {total} |")
    if total > 0:
        lines.append(f"| Passed | {passed} ({passed/total*100:.1f}%) |")
        lines.append(f"| Failed | {failed} ({failed/total*100:.1f}%) |")
    else:
        lines.append("| Passed | 0 (0%) |")
        lines.append("| Failed | 0 (0%) |")
    lines.append("")
    
    # RAGAS 指标概览
    ragas_data = report_data.get("ragas", {})
    if ragas_data and ragas_data.get("ok"):
        lines.append("## RAGAS Metrics Overview")
        lines.append("")
        
        metrics = ragas_data.get("metrics", {})
        
        # 按类别分组显示
        categories = {
            "Context Quality": [k for k in metrics.keys() if "context" in k.lower()],
            "Answer Quality": [k for k in metrics.keys() if any(x in k.lower() for x in ["answer", "faithful"])],
            "Robustness": [k for k in metrics.keys() if any(x in k.lower() for x in ["noise", "completeness"])],
        }
        
        for category_name, metric_keys in categories.items():
            if metric_keys:
                lines.append(f"### {category_name}")
                lines.append("")
                lines.append("| Metric | Score | Status |")
                lines.append("|--------|-------|--------|")
                
                for key in sorted(metric_keys):
                    if key == "ragas_samples_evaluated":
                        continue
                    value = metrics.get(key, 0.0)
                    # 简化指标名称
                    display_name = key.replace("ragas_", "").replace("_", " ").title()
                    # 状态判断
                    if value >= 0.8:
                        status = "✅ Excellent"
                    elif value >= 0.6:
                        status = "🟡 Good"
                    else:
                        status = "🔴 Needs Improvement"
                    lines.append(f"| {display_name} | {value:.3f} | {status} |")
                lines.append("")
    
    # 详细样本结果
    if samples:
        lines.append("## Sample Details")
        lines.append("")
        
        for i, sample in enumerate(samples, 1):
            lines.append(f"### Sample {i}: {sample.get('id', 'N/A')}")
            lines.append("")
            
            # 问题
            lines.append(f"**Question:** {sample.get('question', 'N/A')}")
            lines.append("")
            
            # 状态
            passed = sample.get("passed", False)
            status_icon = "✅" if passed else "❌"
            lines.append(f"**Status:** {status_icon} {'PASS' if passed else 'FAIL'}")
            lines.append("")
            
            # 答案摘要
            answer = sample.get("answer", "")
            if len(answer) > 200:
                answer = answer[:200] + "..."
            lines.append(f"**Answer Preview:** {answer}")
            lines.append("")
            
            # 指标
            if "metrics" in sample:
                lines.append("**Metrics:**")
                for k, v in sample.get("metrics", {}).items():
                    if isinstance(v, (int, float)):
                        lines.append(f"- {k}: {v:.3f}")
                lines.append("")
            
            # 分隔线
            lines.append("---")
            lines.append("")
    
    # 原始分数（可选）
    if include_raw_scores and ragas_data:
        raw_scores = ragas_data.get("raw_scores", {})
        if raw_scores:
            lines.append("## Raw Scores (Per Sample)")
            lines.append("")
            lines.append("| Metric | " + " | ".join([f"S{i+1}" for i in range(len(samples))]) + " | Mean |")
            lines.append("|--------|" + "|".join(["-----"] * len(samples)) + "|------|")
            
            for metric_name, scores in sorted(raw_scores.items()):
                row = [metric_name.replace("ragas_", "")]
                for score in scores:
                    row.append(f"{score:.2f}")
                mean_score = sum(scores) / len(scores) if scores else 0
                row.append(f"{mean_score:.2f}")
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
    
    # 建议
    lines.append("## Recommendations")
    lines.append("")
    
    if ragas_data and ragas_data.get("ok"):
        metrics = ragas_data.get("metrics", {})
        
        # 找出低分指标
        low_metrics = []
        for key, value in metrics.items():
            if key != "ragas_samples_evaluated" and isinstance(value, float):
                if value < 0.6:
                    low_metrics.append((key, value))
        
        if low_metrics:
            lines.append("### Areas for Improvement")
            lines.append("")
            for key, value in sorted(low_metrics, key=lambda x: x[1]):
                display_name = key.replace("ragas_", "").replace("_", " ").title()
                lines.append(f"- **{display_name}** ({value:.3f}): Consider reviewing retrieved contexts or answer generation logic.")
            lines.append("")
        else:
            lines.append("✅ All metrics are performing well!")
            lines.append("")
    
    # 写入文件
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    
    return output_path


def generate_comparison_report(
    *,
    current_report: dict[str, Any],
    baseline_report: dict[str, Any],
    output_path: Path,
    title: str = "RAG Evaluation Comparison",
) -> Path:
    """生成对比报告（当前 vs 基线）."""
    lines = []
    
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 获取指标
    current_metrics = current_report.get("ragas", {}).get("metrics", {})
    baseline_metrics = baseline_report.get("ragas", {}).get("metrics", {})
    
    lines.append("## Metrics Comparison")
    lines.append("")
    lines.append("| Metric | Baseline | Current | Change | Status |")
    lines.append("|--------|----------|---------|--------|--------|")
    
    all_keys = set(current_metrics.keys()) | set(baseline_metrics.keys())
    for key in sorted(all_keys):
        if key == "ragas_samples_evaluated":
            continue
        
        baseline_val = baseline_metrics.get(key, 0.0)
        current_val = current_metrics.get(key, 0.0)
        change = current_val - baseline_val
        
        display_name = key.replace("ragas_", "").replace("_", " ").title()
        change_str = f"{change:+.3f}"
        
        # 状态
        if abs(change) < 0.05:
            status = "➡️ No Change"
        elif change > 0:
            status = "🟢 Improved"
        else:
            status = "🔴 Regressed"
        
        lines.append(f"| {display_name} | {baseline_val:.3f} | {current_val:.3f} | {change_str} | {status} |")
    
    lines.append("")
    
    # 写入文件
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    
    return output_path
