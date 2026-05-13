from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AnswerEvalResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    details: dict[str, Any]
    thresholds: dict[str, float]
    error: str | None = None


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "what",
    "how",
    "why",
    "的",
    "了",
    "在",
    "是",
}


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(text or "").lower())
    return {token for token in raw if token and token not in _STOPWORDS}


def _heuristic_answer_relevancy(question: str, answer: str) -> float:
    q = _tokens(question)
    a = _tokens(answer)
    if not q or not a:
        return 0.0
    overlap = len(q & a)
    return float(overlap) / float(max(1, len(q)))


def build_answer_eval(
    *,
    samples: list[dict[str, Any]],
    citation_coverage: float,
    citation_precision_result: dict[str, Any] | None,
    ragas_result: dict[str, Any] | None,
    thresholds: dict[str, float],
) -> AnswerEvalResult:
    sentence_support_rate = 0.0
    unsupported_sentence_rate = 0.0
    sample_details: list[dict[str, Any]] = []
    if citation_precision_result and bool(citation_precision_result.get("ok")):
        metrics = citation_precision_result.get("metrics") or {}
        if isinstance(metrics, dict):
            sentence_support_rate = float(metrics.get("sentence_support_rate", 0.0) or 0.0)
            unsupported_sentence_rate = float(metrics.get("unsupported_sentence_rate", 0.0) or 0.0)
        raw_details = citation_precision_result.get("details")
        if isinstance(raw_details, list):
            sample_details = [detail for detail in raw_details if isinstance(detail, dict)]

    faithfulness = sentence_support_rate
    answer_relevancy = 0.0
    ragas_metrics = {}
    if ragas_result and bool(ragas_result.get("ok")):
        raw = ragas_result.get("metrics")
        if isinstance(raw, dict):
            ragas_metrics = raw
            faithfulness = float(raw.get("ragas_faithfulness", faithfulness) or faithfulness)
            answer_relevancy = float(raw.get("ragas_answer_relevancy", 0.0) or 0.0)
    if answer_relevancy <= 0.0:
        heuristic_scores = [
            _heuristic_answer_relevancy(str(sample.get("question", "")), str(sample.get("answer", "")))
            for sample in samples
            if str(sample.get("answer", "")).strip()
        ]
        if heuristic_scores:
            answer_relevancy = float(sum(heuristic_scores)) / float(len(heuristic_scores))

    metrics = {
        "citation_coverage": float(citation_coverage),
        "faithfulness": float(faithfulness),
        "answer_relevancy": float(answer_relevancy),
        "sentence_support_rate": float(sentence_support_rate),
        "unsupported_sentence_rate": float(unsupported_sentence_rate),
    }
    return AnswerEvalResult(
        enabled=True,
        ok=True,
        metrics=metrics,
        thresholds=thresholds,
        details={
            "metric_sources": {
                "citation_coverage": "citations",
                "faithfulness": "ragas" if "ragas_faithfulness" in ragas_metrics else "sentence_support",
                "answer_relevancy": "ragas" if "ragas_answer_relevancy" in ragas_metrics else "heuristic_overlap",
            },
            "samples": sample_details,
        },
    )
