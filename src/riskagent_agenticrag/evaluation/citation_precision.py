from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from riskagent_agenticrag.evaluation.judge_llm import get_judge_llm


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


def _split_sentences(text: str) -> list[str]:
    t = str(text or "").strip()
    if not t:
        return []
    parts = re.split(r"[。！？!?\.]+\s*|\n+", t)
    out = [p.strip() for p in parts if p and p.strip()]
    return out


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
    "we",
    "you",
    "i",
    "they",
    "he",
    "she",
    "them",
    "us",
    "our",
    "your",
    "的",
    "了",
    "在",
    "是",
    "和",
    "与",
    "及",
    "或",
    "也",
    "都",
    "就",
    "而",
    "对",
    "把",
    "将",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(text or "").lower())
    out: list[str] = []
    for r in raw:
        if r in _STOPWORDS:
            continue
        if len(r) <= 1 and not re.match(r"[\u4e00-\u9fff]+", r):
            continue
        out.append(r)
    return out


def _heuristic_supported(*, sentence: str, contexts: list[str], threshold: float) -> bool:
    s = sentence.strip()
    if not s:
        return True
    stoks = _tokens(s)
    if not stoks:
        return True

    stoks_set = set(stoks)
    for ctx in contexts:
        c = str(ctx or "")
        if not c:
            continue
        if len(s) >= 12 and s in c:
            return True
        ctoks = set(_tokens(c))
        overlap = len(stoks_set & ctoks)
        recall = overlap / max(1, len(stoks_set))
        if overlap >= 2 and recall >= threshold:
            return True
    return False


def try_compute_citation_precision(
    *,
    samples: list[dict[str, Any]],
    mode: str = "auto",
) -> CitationPrecisionResult:
    effective_mode = (mode or "auto").lower().strip()
    if effective_mode not in {"auto", "llm", "heuristic"}:
        raise ValueError("citation judge mode must be auto llm or heuristic")

    judge_llm = None
    used_mode = effective_mode
    if effective_mode in {"auto", "llm"}:
        try:
            judge_llm = get_judge_llm()
            used_mode = "llm"
        except Exception:
            if effective_mode == "llm":
                raise
            used_mode = "heuristic"

    judged = 0
    skipped = 0
    errors = 0
    sum_precision = 0.0
    hallucinated = 0
    total_sentences_sum = 0
    supported_sentences_sum = 0
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

        try:
            sentences = _split_sentences(answer)
            if used_mode == "llm":
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
                assert judge_llm is not None
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
                supported = [sentence for sentence in sentences if sentence not in unsupported][:supported_sentences]
            else:
                threshold = float(os.getenv("EVAL_CITATION_HEURISTIC_THRESHOLD", "0.5"))
                sentence_support = [
                    (sentence, _heuristic_supported(sentence=sentence, contexts=contexts, threshold=threshold))
                    for sentence in sentences
                ]
                total_sentences = len(sentence_support)
                supported = [sentence for sentence, ok in sentence_support if ok]
                unsupported = [sentence for sentence, ok in sentence_support if not ok][:5]
                supported_sentences = len(supported)
                precision = float(supported_sentences) / float(max(1, total_sentences))

            if total_sentences <= 0:
                raise ValueError("invalid total_sentences")
            if supported_sentences < 0 or supported_sentences > total_sentences:
                raise ValueError("invalid supported_sentences")
            if precision < 0.0 or precision > 1.0:
                raise ValueError("invalid citation_precision")

            judged += 1
            sum_precision += precision
            total_sentences_sum += total_sentences
            supported_sentences_sum += supported_sentences
            if unsupported:
                hallucinated += 1
            details.append(
                {
                    "id": sid,
                    "citation_precision": precision,
                    "total_sentences": total_sentences,
                    "supported_sentences_count": supported_sentences,
                    "supported_sentences": supported[:5],
                    "unsupported_sentences": unsupported,
                    "mode": used_mode,
                }
            )
        except Exception as e:
            errors += 1
            details.append({"id": sid, "error": _to_text(e), "mode": used_mode})

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
        "hallucination_rate_in_citations": hallucinated / judged,
        "sentence_support_rate": float(supported_sentences_sum) / float(max(1, total_sentences_sum)),
        "unsupported_sentence_rate": 1.0 - (float(supported_sentences_sum) / float(max(1, total_sentences_sum))),
        "judged": float(judged),
        "skipped": float(skipped),
        "errors": float(errors),
    }
    return CitationPrecisionResult(enabled=True, ok=True, metrics=metrics, details=details)
