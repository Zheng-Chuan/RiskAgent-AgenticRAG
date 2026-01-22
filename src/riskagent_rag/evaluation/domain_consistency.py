from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DomainConsistencyResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    details: dict[str, Any]
    error: Optional[str] = None


_MVP_GLOSSARY_FORBIDDEN: dict[str, list[str]] = {
    "delta": ["差值", "difference between"],
    "gamma": ["射线", "ray"],
    "vega": ["star", "星星"],
    "theta": ["angle", "角度"],
}


def _extract_numbers(text: str) -> list[float]:
    t = str(text or "")
    matches = re.findall(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?", t)
    out: list[float] = []
    for m in matches:
        try:
            raw = m.replace(",", "")
            is_pct = raw.endswith("%")
            raw = raw[:-1] if is_pct else raw
            v = float(raw)
            out.append(v / 100.0 if is_pct else v)
        except ValueError:
            continue
    return out


def _numeric_supported(*, value: float, candidates: list[float], tolerance: float) -> bool:
    for c in candidates:
        if abs(value - c) <= tolerance:
            return True
        if abs(c) > 1e-9 and abs((value - c) / c) <= tolerance:
            return True
    return False


def _compute_numeric_consistency(*, answer: str, contexts: list[str], tolerance: float) -> dict[str, Any]:
    answer_nums = _extract_numbers(answer)
    if not answer_nums:
        return {"score": 1.0, "total_numbers": 0, "matched_numbers": 0, "unmatched_values": []}

    context_nums = _extract_numbers(" ".join([str(c or "") for c in contexts]))
    matched = 0
    unmatched: list[float] = []
    for n in answer_nums:
        if _numeric_supported(value=n, candidates=context_nums, tolerance=tolerance):
            matched += 1
        else:
            unmatched.append(float(n))

    score = matched / max(1, len(answer_nums))
    return {
        "score": float(score),
        "total_numbers": int(len(answer_nums)),
        "matched_numbers": int(matched),
        "unmatched_values": unmatched,
    }


def _compute_glossary_consistency(*, answer: str) -> dict[str, Any]:
    a = str(answer or "")
    al = a.lower()
    checked = 0
    violations: list[dict[str, Any]] = []

    for term, forbidden in _MVP_GLOSSARY_FORBIDDEN.items():
        if term in al:
            checked += 1
            for bad in forbidden:
                if str(bad).lower() in al:
                    violations.append({"term": term, "forbidden_word": bad})
                    break

    if checked <= 0:
        return {"score": 1.0, "checked_terms": 0, "violations": []}

    score = (checked - len(violations)) / checked
    return {"score": float(score), "checked_terms": int(checked), "violations": violations}


def try_compute_domain_consistency(*, samples: list[dict[str, Any]], tolerance: float = 0.01) -> DomainConsistencyResult:
    try:
        tol = float(tolerance)
    except (TypeError, ValueError):
        tol = 0.01

    numeric_scores: list[float] = []
    glossary_scores: list[float] = []
    per_sample: list[dict[str, Any]] = []

    try:
        for s in samples:
            sid = s.get("id")
            answer = str(s.get("answer", ""))
            contexts = s.get("contexts", [])
            if not isinstance(contexts, list):
                contexts = []

            num = _compute_numeric_consistency(answer=answer, contexts=contexts, tolerance=tol)
            glo = _compute_glossary_consistency(answer=answer)
            numeric_scores.append(float(num["score"]))
            glossary_scores.append(float(glo["score"]))
            per_sample.append({"id": sid, "numeric": num, "glossary": glo})

        n = len(samples) if samples else 0
        if n <= 0:
            return DomainConsistencyResult(enabled=True, ok=True, metrics={}, details={"samples": []})

        numeric_mean = sum(numeric_scores) / n
        glossary_mean = sum(glossary_scores) / n
        metrics = {
            "numeric_consistency_score": float(numeric_mean),
            "glossary_consistency_score": float(glossary_mean),
            "domain_consistency_score": float((numeric_mean + glossary_mean) / 2.0),
        }
        return DomainConsistencyResult(enabled=True, ok=True, metrics=metrics, details={"samples": per_sample})
    except Exception as e:
        return DomainConsistencyResult(enabled=True, ok=False, metrics={}, details={"samples": per_sample}, error=str(e))
