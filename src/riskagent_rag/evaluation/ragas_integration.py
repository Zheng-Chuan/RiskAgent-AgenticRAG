"""RAGAS integration.

中文注释 可选集成 默认不开启
目标 计算 triad 和 retrieval metrics 并写入评测报告
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
) -> RagasResult:
    try:
        from datasets import Dataset
    except ImportError as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"datasets not available {e}")

    try:
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"ragas not available {e}")

    # 准备数据
    rows: list[dict[str, Any]] = []
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

        gt = s.get("ground_truth_contexts")
        if isinstance(gt, list) and gt:
            row["ground_truth"] = str(gt[0])  # RAGAS expect string or list? v0.1+ expects 'ground_truth' col
            # 注意: context_recall 需要 ground_truth
            # 这里简化处理, 如果有 gt contexts, 拼成 string 或者 list?
            # RAGAS 0.1+ dataset schema: question, answer, contexts, ground_truth
            # ground_truth should be string (the reference answer) or list of strings?
            # 通常 ground_truth 是 reference answer.
            # 但 context recall 需要的是 ground truth contexts 吗?
            # RAGAS 文档: context_recall measures extent to which retrieved context aligns with ground truth answer.
            # Wait, context_recall compares ground_truth (answer) vs contexts?
            # actually context_recall: "Is the ground truth answer present in the contexts?"
            # So we need reference_answer as ground_truth.

        ref = s.get("reference_answer")
        if isinstance(ref, str) and ref:
            row["ground_truth"] = ref

        rows.append(row)

    if not rows:
        return RagasResult(enabled=True, ok=False, metrics={}, error="no samples provided")

    ds = Dataset.from_list(rows)

    # 准备 Metrics
    metrics_list = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    # 准备 LLM 和 Embeddings
    judge_llm = get_judge_llm()
    embeddings = build_embeddings()

    # 执行评测
    try:
        # RAGAS v0.1+ evaluate signature:
        # evaluate(dataset, metrics, llm=..., embeddings=...)
        # 注意: 如果 judge_llm 为 None, RAGAS 会尝试默认 OpenAI.
        # 如果 embeddings 为 None, RAGAS 会尝试默认 OpenAI.
        # 我们显式传入 embeddings (HuggingFace), 以免 RAGAS 报错缺少 OpenAI Key (如果用户只用本地).
        result = evaluate(
            dataset=ds,
            metrics=metrics_list,
            llm=judge_llm,
            embeddings=embeddings,
        )
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=str(e))

    # 提取结果
    metrics_out: dict[str, float] = {}
    # RAGAS result object acts like a dict with averages
    try:
        # result is a Result object, can be cast to dict for averages
        # e.g. {'faithfulness': 0.8, ...}
        for k, v in result.items():
            try:
                metrics_out[k] = float(v)
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    return RagasResult(enabled=True, ok=True, metrics=metrics_out)
