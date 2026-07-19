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
    "explain",
    "describe",
    "context",
    "meaning",
    "的",
    "了",
    "在",
    "是",
}


def _normalize_token(token: str) -> str:
    token = str(token or "").strip().lower()
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(text or "").lower())
    normalized = (_normalize_token(token) for token in raw)
    return {token for token in normalized if token and token not in _STOPWORDS}


def _overlap_ratio(expected_tokens: set[str], actual_tokens: set[str]) -> float:
    if not expected_tokens or not actual_tokens:
        return 0.0
    overlap = len(expected_tokens & actual_tokens)
    return float(overlap) / float(max(1, len(expected_tokens)))


def _heuristic_answer_relevancy(question: str, answer: str, reference_answer: str | None = None) -> float:
    q = _tokens(question)
    a = _tokens(answer)
    if not q or not a:
        return 0.0

    question_overlap = _overlap_ratio(q, a)
    reference_overlap = 0.0
    if reference_answer:
        r = _tokens(reference_answer)
        reference_overlap = _overlap_ratio(r, a)

    if reference_overlap <= 0.0:
        return float(question_overlap)
    return float(max(question_overlap, (0.6 * question_overlap) + (0.4 * reference_overlap)))


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
            _heuristic_answer_relevancy(
                str(sample.get("question", "")),
                str(sample.get("answer", "")),
                str(sample.get("reference_answer", "") or ""),
            )
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
