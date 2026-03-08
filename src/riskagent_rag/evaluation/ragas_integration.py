"""RAGAS integration.

中文注释 RAGAS 质量指标集成 (v0.4.3+)
- 使用 ragas.metrics.collections 新导入路径
- 提供 Triad + Retrieval 完整指标集
- 替代自建的 citation_precision，提供更成熟的质量评估
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from riskagent_rag.rag.embeddings import build_embeddings
from riskagent_rag.evaluation.judge_llm import get_judge_llm


@dataclass(frozen=True)
class RagasResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    error: Optional[str] = None


def try_compute_ragas_metrics(
    *,
    samples: list[dict[str, Any]],
    include_reference_based: bool = True,
) -> RagasResult:
    """Compute RAGAS metrics for evaluation samples.
    
    Args:
        samples: Evaluation samples with question, answer, contexts
        include_reference_based: Whether to include metrics requiring reference_answer
    
    Returns:
        RagasResult with metrics dict containing:
        - faithfulness: Answer groundedness in contexts (0-1)
        - answer_relevancy: Answer relevance to question (0-1)  
        - context_precision: Precision of retrieved contexts (0-1)
        - context_recall: Recall based on reference answer (0-1)
        - answer_correctness: Correctness vs reference (0-1)
        - factual_correctness: Factual accuracy (0-1)
    """
    try:
        from datasets import Dataset
    except ImportError as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"datasets not available: {e}")

    try:
        # RAGAS 0.4.3+ 新导入路径
        from ragas.metrics.collections import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
            factual_correctness,
        )
    except ImportError as e:
        # Fallback to old import path for compatibility
        try:
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
                answer_correctness,
            )
            factual_correctness = None
        except ImportError as e2:
            return RagasResult(enabled=True, ok=False, metrics={}, error=f"ragas not available: {e2}")

    # 准备数据
    rows: list[dict[str, Any]] = []
    has_reference = False
    
    for s in samples:
        question = str(s.get("question", ""))
        answer = str(s.get("answer", ""))
        contexts = s.get("contexts")
        if not isinstance(contexts, list):
            contexts = []
        contexts = [str(c) for c in contexts]

        row: dict[str, Any] = {
            "question": question,
            "answer": answer,
            "contexts": contexts,
        }

        # 优先使用 reference_answer 作为 ground_truth
        ref = s.get("reference_answer")
        if isinstance(ref, str) and ref.strip():
            row["ground_truth"] = ref
            has_reference = True
        elif isinstance(ref, list) and ref:
            row["ground_truth"] = str(ref[0])
            has_reference = True

        rows.append(row)

    if not rows:
        return RagasResult(enabled=True, ok=False, metrics={}, error="no samples provided")

    ds = Dataset.from_list(rows)

    # 准备 Metrics
    metrics_list = [
        faithfulness,
        answer_relevancy,
        context_precision,
    ]
    
    # context_recall 和 answer_correctness 需要 reference_answer
    if include_reference_based and has_reference:
        metrics_list.append(context_recall)
        metrics_list.append(answer_correctness)
        if factual_correctness is not None:
            metrics_list.append(factual_correctness)

    # 准备 LLM 和 Embeddings
    try:
        judge_llm = get_judge_llm()
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"LLM setup failed: {e}")
    
    try:
        embeddings = build_embeddings()
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"Embeddings setup failed: {e}")

    # 执行评测
    try:
        from ragas import evaluate
        
        result = evaluate(
            dataset=ds,
            metrics=metrics_list,
            llm=judge_llm,
            embeddings=embeddings,
        )
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"RAGAS evaluation failed: {e}")

    # 提取结果
    metrics_out: dict[str, float] = {}
    try:
        # RAGAS result 是可迭代的字典类对象
        for k, v in result.items():
            try:
                # 处理可能的嵌套结构
                if isinstance(v, (int, float)):
                    metrics_out[f"ragas_{k}"] = float(v)
                elif hasattr(v, 'mean'):
                    metrics_out[f"ragas_{k}"] = float(v.mean())
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    # 添加元数据
    metrics_out["ragas_samples_evaluated"] = len(rows)
    metrics_out["ragas_reference_based"] = 1.0 if (include_reference_based and has_reference) else 0.0

    return RagasResult(enabled=True, ok=True, metrics=metrics_out)


def get_ragas_metrics_description() -> dict[str, str]:
    """Get description of RAGAS metrics for documentation."""
    return {
        "ragas_faithfulness": "RAGAS Faithfulness - Measures if answer is grounded in retrieved contexts (0-1, higher is better)",
        "ragas_answer_relevancy": "RAGAS Answer Relevancy - Measures how relevant the answer is to the question (0-1, higher is better)",
        "ragas_context_precision": "RAGAS Context Precision - Measures precision of retrieved contexts (0-1, higher is better)",
        "ragas_context_recall": "RAGAS Context Recall - Measures recall of relevant contexts vs reference answer (0-1, higher is better, requires reference)",
        "ragas_answer_correctness": "RAGAS Answer Correctness - Measures correctness vs reference answer (0-1, higher is better, requires reference)",
        "ragas_factual_correctness": "RAGAS Factual Correctness - Measures factual accuracy (0-1, higher is better, requires reference)",
    }
