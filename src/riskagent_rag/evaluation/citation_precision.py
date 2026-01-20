from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from riskagent_rag.evaluation.judge_llm import get_judge_llm


@dataclass(frozen=True)
class CitationPrecisionResult:
    enabled: bool
    ok: bool
    metrics: dict[str, float]
    details: list[dict[str, Any]]
    error: Optional[str] = None


def _to_text(x: Any) -> str:
    if x is None:
        return ""
    return str(x)


def _read_content(x: Any) -> str:
    if hasattr(x, "content"):
        return _to_text(getattr(x, "content"))
    return _to_text(x)


def try_compute_citation_precision(
    *,
    samples: list[dict[str, Any]],
) -> CitationPrecisionResult:
    judge_llm = get_judge_llm()
    if judge_llm is None:
        return CitationPrecisionResult(
            enabled=True,
            ok=False,
            metrics={},
            details=[],
            error="judge llm not available",
        )

    judged = 0
    skipped = 0
    parse_errors = 0
    sum_precision = 0.0
    details: list[dict[str, Any]] = []

    for s in samples:
        sid = _to_text(s.get("id"))
        question = _to_text(s.get("question"))
        answer = _to_text(s.get("answer"))
        contexts = s.get("contexts")
        if not isinstance(contexts, list):
            contexts = []
        contexts = [_to_text(c) for c in contexts if _to_text(c).strip()]

        if not answer.strip() or not contexts:
            skipped += 1
            continue

        prompt = json.dumps(
            {
                "task": "citation_precision_judge",
                "instruction": (
                    "You are a strict evaluator for grounded QA. "
                    "Decide how much of the answer is supported by the provided contexts. "
                    "Return JSON only and no markdown."
                ),
                "schema": {
                    "total_sentences": "int >= 1",
                    "supported_sentences": "int between 0 and total_sentences",
                    "citation_precision": "float between 0 and 1",
                    "unsupported_sentences": "list of strings max 5",
                },
                "input": {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                },
            },
            ensure_ascii=False,
        )

        try:
            raw = judge_llm.invoke(prompt)
            content = _read_content(raw).strip()
            parsed = json.loads(content)
            total_sentences = int(parsed.get("total_sentences", 0))
            supported_sentences = int(parsed.get("supported_sentences", 0))
            precision = float(parsed.get("citation_precision", 0.0))
            unsupported = parsed.get("unsupported_sentences", [])
            if not isinstance(unsupported, list):
                unsupported = []
            unsupported = [_to_text(u) for u in unsupported][:5]

            if total_sentences <= 0:
                raise ValueError("invalid total_sentences")
            if supported_sentences < 0 or supported_sentences > total_sentences:
                raise ValueError("invalid supported_sentences")
            if precision < 0.0 or precision > 1.0:
                raise ValueError("invalid citation_precision")

            judged += 1
            sum_precision += precision
            details.append(
                {
                    "id": sid,
                    "citation_precision": precision,
                    "total_sentences": total_sentences,
                    "supported_sentences": supported_sentences,
                    "unsupported_sentences": unsupported,
                }
            )
        except Exception as e:
            parse_errors += 1
            details.append({"id": sid, "error": _to_text(e)})

    if judged <= 0:
        return CitationPrecisionResult(
            enabled=True,
            ok=False,
            metrics={},
            details=details,
            error="no samples judged",
        )

    mean_precision = sum_precision / judged
    metrics = {
        "citation_precision": mean_precision,
        "judged": float(judged),
        "skipped": float(skipped),
        "parse_errors": float(parse_errors),
    }
    return CitationPrecisionResult(enabled=True, ok=True, metrics=metrics, details=details)

