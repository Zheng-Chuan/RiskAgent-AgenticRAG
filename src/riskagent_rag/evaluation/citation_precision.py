from __future__ import annotations

import json
import os
import re
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
    env_mode = os.getenv("EVAL_CITATION_JUDGE_MODE", "").lower().strip()
    effective_mode = (env_mode or mode or "auto").lower().strip()
    if effective_mode not in {"auto", "llm", "heuristic"}:
        effective_mode = "auto"

    judge_llm = get_judge_llm() if effective_mode in {"auto", "llm"} else None
    if effective_mode == "llm" and judge_llm is None:
        return CitationPrecisionResult(
            enabled=True,
            ok=False,
            metrics={},
            details=[],
            error="judge llm not available",
        )

    heuristic_threshold = float(os.getenv("EVAL_CITATION_HEURISTIC_THRESHOLD", "0.25"))

    judged = 0
    skipped = 0
    errors = 0
    sum_precision = 0.0
    hallucinated = 0
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
            if judge_llm is None:
                sentences = _split_sentences(answer)
                total_sentences = max(1, len(sentences))
                unsupported_sentences: list[str] = []
                supported_sentences = 0
                for sent in sentences:
                    if _heuristic_supported(sentence=sent, contexts=contexts, threshold=heuristic_threshold):
                        supported_sentences += 1
                    else:
                        unsupported_sentences.append(sent)
                precision = supported_sentences / max(1, total_sentences)
                unsupported = unsupported_sentences[:5]
            else:
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
            if unsupported:
                hallucinated += 1
            details.append(
                {
                    "id": sid,
                    "citation_precision": precision,
                    "total_sentences": total_sentences,
                    "supported_sentences": supported_sentences,
                    "unsupported_sentences": unsupported,
                    "mode": "llm" if judge_llm is not None else "heuristic",
                }
            )
        except Exception as e:
            errors += 1
            details.append({"id": sid, "error": _to_text(e), "mode": "llm" if judge_llm is not None else "heuristic"})

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
        "judged": float(judged),
        "skipped": float(skipped),
        "errors": float(errors),
    }
    return CitationPrecisionResult(enabled=True, ok=True, metrics=metrics, details=details)
