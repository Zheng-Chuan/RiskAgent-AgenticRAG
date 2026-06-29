"""Self-RAG -- 文档与生成质量评分."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.rag.utils import token_set


_QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "between",
    "compare",
    "difference",
    "does",
    "explain",
    "for",
    "how",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "vs",
    "versus",
    "what",
    "why",
}
_NUMERIC_HINT_TOKENS = {
    "abs",
    "breach",
    "capital",
    "count",
    "delta",
    "discount",
    "ead",
    "es",
    "exposure",
    "factor",
    "lgd",
    "limit",
    "margin",
    "maturity",
    "notional",
    "percent",
    "probability",
    "shortfall",
    "threshold",
    "var",
    "vega",
}
_NUMERIC_EVIDENCE_TOKENS = {
    "discount",
    "ead",
    "es",
    "lgd",
    "maturity",
    "notional",
    "percent",
    "probability",
    "shortfall",
    "var",
}


def should_require_numeric_backing(*, question: str) -> bool:
    q = str(question or "").lower()
    if any(x in q for x in ("delta", "breach", "exposure", "limit")):
        return True
    return False


@dataclass(frozen=True)
class SelfRagDocGrade:
    doc_idx: int
    parent_id: str
    chunk_id: str
    isrel: float
    issup: float
    isuse: float


@dataclass(frozen=True)
class SelfRagRetrievalGrade:
    sufficient: bool
    reason: str
    top_isrel: float
    avg_isrel: float
    grades: list[SelfRagDocGrade]
    question_type: str = "default"
    query_coverage: float = 0.0
    source_diversity: int = 0
    parent_diversity: int = 0
    numeric_evidence: bool = False


def _question_type(*, question: str) -> str:
    q = str(question or "").lower()
    if should_require_numeric_backing(question=question):
        return "numeric"
    if any(x in q for x in ("difference", "compare", "vs", "versus", "distinguish", "contrast", "between")):
        return "compare"
    if any(x in q for x in ("how", "procedure", "process", "workflow", "steps")):
        return "procedure"
    if any(x in q for x in ("what is", "define", "meaning of", "stands for")):
        return "definition"
    return "default"


def _focus_tokens(*, question: str) -> set[str]:
    toks = token_set(question)
    return {
        tok
        for tok in toks
        if len(tok) >= 2 and tok not in _QUESTION_STOPWORDS
    }


def _has_numeric_evidence(*, docs: list[Document], focus_tokens: set[str]) -> bool:
    for d in docs:
        meta = d.metadata or {}
        text = " ".join(
            [
                str(meta.get("expanded_text") or ""),
                str(d.page_content or ""),
                str(meta.get("section_path") or ""),
            ]
        ).lower()
        toks = token_set(text)
        if any(ch.isdigit() for ch in text):
            return True
        if focus_tokens & _NUMERIC_EVIDENCE_TOKENS and toks & _NUMERIC_EVIDENCE_TOKENS:
            return True
    return False


def grade_docs(*, question: str, docs: list[Document]) -> SelfRagRetrievalGrade:
    q_toks = token_set(question)
    q_focus = _focus_tokens(question=question)
    kind = _question_type(question=question)
    if not docs:
        return SelfRagRetrievalGrade(
            sufficient=False,
            reason="no_docs",
            top_isrel=0.0,
            avg_isrel=0.0,
            grades=[],
            question_type=kind,
        )

    grades: list[SelfRagDocGrade] = []
    isrels: list[float] = []
    source_ids: set[str] = set()
    parent_ids: set[str] = set()
    union_doc_tokens: set[str] = set()
    for i, d in enumerate(docs):
        meta = d.metadata or {}
        text = str(meta.get("expanded_text") or d.page_content or "")
        dt = token_set(text)
        union_doc_tokens |= dt
        overlap = len(q_toks & dt) if q_toks else 0
        denom = max(8, len(q_toks)) if q_toks else 8
        isrel = float(overlap) / float(denom)

        issup = 1.0 if overlap >= 2 else 0.0

        gap = meta.get("confidence_gap_to_top1")
        if isinstance(gap, (int, float)):
            isuse = 1.0 if float(gap) <= 0.4 else 0.0
        else:
            isuse = 1.0 if isrel >= 0.15 else 0.0

        grades.append(
            SelfRagDocGrade(
                doc_idx=int(i),
                parent_id=str(meta.get("parent_id") or ""),
                chunk_id=str(meta.get("chunk_id") or ""),
                isrel=float(isrel),
                issup=float(issup),
                isuse=float(isuse),
            )
        )
        isrels.append(isrel)
        source = str(meta.get("source") or "").strip()
        parent_id = str(meta.get("parent_id") or "").strip()
        if source:
            source_ids.add(source)
        if parent_id:
            parent_ids.add(parent_id)

    top_isrel = float(max(isrels, default=0.0))
    avg_isrel = float(sum(isrels) / float(len(isrels))) if isrels else 0.0
    query_coverage = float(len(q_focus & union_doc_tokens)) / float(max(1, len(q_focus))) if q_focus else 0.0
    source_diversity = len(source_ids)
    parent_diversity = len(parent_ids)
    numeric_evidence = _has_numeric_evidence(docs=docs, focus_tokens=q_focus)

    base_sufficient = bool(top_isrel >= 0.15) and any(g.issup >= 1.0 for g in grades)
    if not base_sufficient:
        sufficient = False
        reason = "low_relevance"
    elif kind == "compare":
        sufficient = bool(query_coverage >= 0.25) and bool(
            source_diversity >= 2 or parent_diversity >= 2 or top_isrel >= 0.35
        )
        reason = "ok_compare" if sufficient else "compare_needs_broader_coverage"
    elif kind == "numeric":
        sufficient = bool(query_coverage >= 0.2) and bool(numeric_evidence)
        reason = "ok_numeric" if sufficient else "numeric_backing_weak"
    elif kind == "procedure":
        sufficient = bool(query_coverage >= 0.2) and bool(parent_diversity >= 1)
        reason = "ok_procedure" if sufficient else "procedure_context_thin"
    else:
        sufficient = bool(query_coverage >= 0.18 or top_isrel >= 0.3)
        reason = "ok" if sufficient else "definition_coverage_thin"
    return SelfRagRetrievalGrade(
        sufficient=sufficient,
        reason=reason,
        top_isrel=top_isrel,
        avg_isrel=avg_isrel,
        grades=grades,
        question_type=kind,
        query_coverage=query_coverage,
        source_diversity=source_diversity,
        parent_diversity=parent_diversity,
        numeric_evidence=numeric_evidence,
    )


def grade_generation(*, failure_reason: dict[str, Any] | None) -> dict[str, Any]:
    if failure_reason is None:
        return {"ok": True, "category": "", "message": ""}
    return {
        "ok": False,
        "category": str(failure_reason.get("category") or ""),
        "message": str(failure_reason.get("message") or ""),
        "details": failure_reason.get("details") or {},
    }
