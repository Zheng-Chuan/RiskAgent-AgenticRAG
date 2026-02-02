from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(str(text or ""))}


def should_require_numeric_backing(*, question: str, should_call_tool: bool) -> bool:
    if should_call_tool:
        return True
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


def grade_docs(*, question: str, docs: list[Document]) -> SelfRagRetrievalGrade:
    q_toks = _tokens(question)
    if not docs:
        return SelfRagRetrievalGrade(
            sufficient=False,
            reason="no_docs",
            top_isrel=0.0,
            avg_isrel=0.0,
            grades=[],
        )

    grades: list[SelfRagDocGrade] = []
    isrels: list[float] = []
    for i, d in enumerate(docs):
        meta = d.metadata or {}
        text = str(meta.get("expanded_text") or d.page_content or "")
        dt = _tokens(text)
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

    top_isrel = float(max(isrels, default=0.0))
    avg_isrel = float(sum(isrels) / float(len(isrels))) if isrels else 0.0

    sufficient = bool(top_isrel >= 0.15) and any(g.issup >= 1.0 for g in grades)
    reason = "ok" if sufficient else "low_relevance"
    return SelfRagRetrievalGrade(
        sufficient=sufficient,
        reason=reason,
        top_isrel=top_isrel,
        avg_isrel=avg_isrel,
        grades=grades,
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

