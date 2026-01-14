"""RAGAS integration.

中文注释 可选集成 默认不开启
目标 计算 triad 和 retrieval metrics 并写入评测报告
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
        from datasets import Dataset  # type: ignore[import-not-found]
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"datasets not available {e}")

    try:
        import ragas  # type: ignore[import-not-found]

        evaluate = getattr(ragas, "evaluate")
        metrics_mod = getattr(ragas, "metrics", None)
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=f"ragas not available {e}")

    if metrics_mod is None:
        return RagasResult(enabled=True, ok=False, metrics={}, error="ragas.metrics not available")

    def _get_metric(name: str):
        return getattr(metrics_mod, name, None)

    selected = {
        "context_relevance": _get_metric("context_relevancy") or _get_metric("context_relevance"),
        "faithfulness": _get_metric("faithfulness"),
        "answer_relevance": _get_metric("answer_relevancy") or _get_metric("answer_relevance"),
        "context_precision": _get_metric("context_precision"),
        "context_recall": _get_metric("context_recall"),
    }

    metrics_list = [m for m in selected.values() if m is not None]
    if not metrics_list:
        return RagasResult(enabled=True, ok=False, metrics={}, error="no ragas metrics found")

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
            row["ground_truths"] = [str(x) for x in gt]

        ref = s.get("reference_answer")
        if isinstance(ref, str) and ref:
            row["ground_truth"] = ref

        rows.append(row)

    ds = Dataset.from_list(rows)

    try:
        result = evaluate(ds, metrics=metrics_list)
    except Exception as e:
        return RagasResult(enabled=True, ok=False, metrics={}, error=str(e))

    metrics_out: dict[str, float] = {}
    for k in selected.keys():
        try:
            val = float(result.get(k))  # type: ignore[call-arg]
            metrics_out[k] = val
        except Exception:
            pass

    if not metrics_out:
        try:
            raw = dict(result)  # type: ignore[arg-type]
            for rk, rv in raw.items():
                try:
                    metrics_out[str(rk)] = float(rv)
                except Exception:
                    continue
        except Exception:
            pass

    return RagasResult(enabled=True, ok=True, metrics=metrics_out)
