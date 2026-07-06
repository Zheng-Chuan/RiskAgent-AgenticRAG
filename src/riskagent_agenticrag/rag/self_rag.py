"""Self-RAG -- 文档与生成质量评分 (claim-aware sufficiency scorer)."""

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
_CLAIM_KEY_WEIGHTS = {
    "definition": {
        "is": 2.0,
        "stands": 2.0,
        "means": 2.0,
        "refers": 2.0,
        "definition": 3.0,
    },
    "compare": {
        "difference": 3.0,
        "similarity": 3.0,
        "versus": 2.0,
        "compared": 2.0,
        "contrast": 2.0,
    },
    "procedure": {
        "steps": 2.0,
        "process": 2.0,
        "workflow": 2.0,
        "first": 1.5,
        "then": 1.5,
        "finally": 1.5,
    },
    "numeric": {
        "formula": 3.0,
        "calculate": 2.5,
        "equals": 2.0,
        "value": 1.5,
        "limit": 2.0,
        "threshold": 2.0,
    },
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
    claim_coverage: float = 0.0
    top_claim_score: float = 0.0
    redundancy_penalty: float = 0.0


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


def _weighted_focus_tokens(*, question: str) -> dict[str, float]:
    """为 query token 分配权重，核心术语权重更高。"""
    q_toks = token_set(question)
    kind = _question_type(question=question)
    weights: dict[str, float] = {}
    for tok in q_toks:
        if len(tok) < 2 or tok in _QUESTION_STOPWORDS:
            weights[tok] = 0.2
        else:
            weights[tok] = 1.0

    # 核心金融术语权重提升
    core_terms = {
        "frtb", "cva", "xva", "dva", "fva", "kva", "mva", "colva",
        "delta", "gamma", "vega", "theta", "rho", "volga", "vanna", "charm",
        "var", "es", "expected", "shortfall", "initial", "margin", "variation",
        "wrong-way", "right-way", "netting", "csa", "collateral",
    }
    for tok in weights:
        if tok in core_terms:
            weights[tok] = 2.5

    # 题型特定关键词权重提升
    claim_weights = _CLAIM_KEY_WEIGHTS.get(kind, {})
    for tok in weights:
        if tok in claim_weights:
            weights[tok] = max(weights[tok], claim_weights[tok])

    return weights


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


def _claim_coverage_score(*, question: str, docs: list[Document]) -> float:
    """计算文档集合对 query 核心 claim 的覆盖度。"""
    q_weights = _weighted_focus_tokens(question=question)
    if not q_weights:
        return 0.0

    kind = _question_type(question=question)
    total_weight = sum(q_weights.values())
    covered_weight = 0.0

    for tok, weight in q_weights.items():
        for d in docs:
            meta = d.metadata or {}
            text = " ".join(
                [
                    str(meta.get("expanded_text") or ""),
                    str(d.page_content or ""),
                ]
            ).lower()
            if tok in text or tok in str(meta.get("section_path", "")).lower():
                covered_weight += weight
                break

    return covered_weight / total_weight if total_weight > 0 else 0.0


def _redundancy_penalty(*, docs: list[Document]) -> float:
    """检测同一 parent 的 chunk 冗余，计算冗余惩罚系数。"""
    if not docs:
        return 0.0

    parent_counts: dict[str, int] = {}
    for d in docs:
        parent_id = str((d.metadata or {}).get("parent_id", "")).strip()
        if parent_id:
            parent_counts[parent_id] = parent_counts.get(parent_id, 0) + 1

    # 如果同一个 parent 出现超过 3 次，给予惩罚
    penalty = 0.0
    for count in parent_counts.values():
        if count > 3:
            penalty += (count - 3) * 0.05
    return min(penalty, 0.3)  # 最大惩罚 0.3


def grade_docs(*, question: str, docs: list[Document]) -> SelfRagRetrievalGrade:
    q_toks = token_set(question)
    q_focus = _focus_tokens(question=question)
    q_weights = _weighted_focus_tokens(question=question)
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

        # 加权相关性计算
        overlap_weighted = 0.0
        total_weight = 0.0
        for tok, weight in q_weights.items():
            total_weight += weight
            if tok in dt:
                overlap_weighted += weight
        denom = max(total_weight, 8.0) if q_weights else 8.0
        isrel = float(overlap_weighted) / float(denom)

        # issup: 判断是否能支持回答（至少覆盖 2 个核心 token）
        issup = 1.0 if overlap_weighted >= 2.0 else 0.0

        # isuse: 判断是否有用（基于 confidence gap 或相关性阈值）
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

    # query_coverage: 基于 focus token 的覆盖
    query_coverage = float(len(q_focus & union_doc_tokens)) / float(max(1, len(q_focus))) if q_focus else 0.0

    # claim_coverage: 基于加权 token 的 claim 覆盖度
    claim_coverage = _claim_coverage_score(question=question, docs=docs)

    source_diversity = len(source_ids)
    parent_diversity = len(parent_ids)
    numeric_evidence = _has_numeric_evidence(docs=docs, focus_tokens=q_focus)
    redundancy_penalty = _redundancy_penalty(docs=docs)

    # 计算 top claim score（最高单文档 claim 覆盖度）
    top_claim_score = 0.0
    for tok, weight in q_weights.items():
        if docs and (tok in (docs[0].page_content or "").lower() or tok in str((docs[0].metadata or {}).get("section_path", "")).lower()):
            top_claim_score += weight
    top_claim_score = top_claim_score / max(sum(q_weights.values()), 1.0) if q_weights else 0.0

    # 基础充分性判断：至少有一个文档相关性足够且有支持能力
    base_sufficient = bool(top_isrel >= 0.2) and any(g.issup >= 1.0 for g in grades)

    if not base_sufficient:
        sufficient = False
        reason = "low_relevance"
    elif kind == "compare":
        # compare: 需要多视角覆盖，claim 覆盖度 >= 0.4，且至少 2 个 source 或 parent
        sufficient = (
            bool(query_coverage >= 0.3)
            and bool(claim_coverage >= 0.4)
            and bool(source_diversity >= 2 or parent_diversity >= 2)
            and bool(top_isrel >= 0.35)
        )
        reason = "ok_compare" if sufficient else "compare_needs_broader_coverage"
    elif kind == "numeric":
        # numeric: 需要数值证据 + claim 覆盖度
        sufficient = (
            bool(query_coverage >= 0.25)
            and bool(claim_coverage >= 0.3)
            and bool(numeric_evidence)
        )
        reason = "ok_numeric" if sufficient else "numeric_backing_weak"
    elif kind == "procedure":
        # procedure: 需要步骤词覆盖 + 上下文 diversity
        sufficient = (
            bool(query_coverage >= 0.25)
            and bool(claim_coverage >= 0.3)
            and bool(parent_diversity >= 1)
        )
        reason = "ok_procedure" if sufficient else "procedure_context_thin"
    elif kind == "definition":
        # definition: 要求更严格，claim 覆盖度 >= 0.4，且 top 文档必须直接回答核心问题
        sufficient = (
            bool(query_coverage >= 0.3)
            and bool(claim_coverage >= 0.4)
            and bool(top_claim_score >= 0.5)
        )
        reason = "ok_definition" if sufficient else "definition_coverage_thin"
    else:
        # default: 通用阈值，需满足 query coverage 和 claim coverage
        sufficient = (
            bool(query_coverage >= 0.25)
            and bool(claim_coverage >= 0.3)
            and bool(top_isrel >= 0.3)
        )
        reason = "ok" if sufficient else "coverage_thin"

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
        claim_coverage=claim_coverage,
        top_claim_score=top_claim_score,
        redundancy_penalty=redundancy_penalty,
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
