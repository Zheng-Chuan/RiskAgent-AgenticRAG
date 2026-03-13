from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from riskagent_agenticrag.rag.utils import doc_key, rrf_scores, tokenize


def _merge_lists_unique(xs: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for x in xs:
        v = str(x or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


_STOPWORDS = {
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "explain",
    "define",
    "介绍",
    "解释",
    "是什么",
    "怎么",
    "如何",
    "为什么",
    "请问",
    "帮我",
}

_ABBREV_EXPANSIONS: dict[str, str] = {
    "frtb": "fundamental review of the trading book",
    "cva": "credit valuation adjustment",
    "xva": "valuation adjustment",
    "var": "value at risk",
    "es": "expected shortfall",
}


@dataclass(frozen=True)
class QueryIntelConfig:
    expansion_n: int = 3
    enable_step_back: bool = True
    enable_decomposition: bool = True
    per_query_k: int = 8
    final_k: int = 4
    rrf_k: int = 60
    max_variants: int = 8


def _keywordize(q: str) -> str:
    toks = tokenize(q)
    kept: list[str] = []
    for t in toks:
        if t in _STOPWORDS:
            continue
        kept.append(t)
    kept = _merge_lists_unique(kept)
    return " ".join(kept[:24]).strip() or str(q or "").strip()


def _expand_abbrev(q: str) -> list[str]:
    toks = tokenize(q)
    found: list[str] = []
    for t in toks:
        if t in _ABBREV_EXPANSIONS:
            found.append(_ABBREV_EXPANSIONS[t])
    if not found:
        return []
    base = str(q or "").strip()
    extra = " ".join(_merge_lists_unique(found))
    return [f"{base} {extra}".strip()]


def _step_back_query(q: str) -> str:
    kw = _keywordize(q)
    toks = kw.split()
    head = " ".join(toks[:6]).strip()
    if not head:
        head = str(q or "").strip()
    return f"overview definition background {head}".strip()


def _decompose(q: str) -> list[str]:
    raw = str(q or "").strip()
    if not raw:
        return []
    parts = re.split(r"\s*(?:and|以及|同时|并且|,|;|/|\\+|&)\s*", raw, flags=re.IGNORECASE)
    out: list[str] = []
    for p in parts:
        p1 = str(p or "").strip()
        if len(p1) < 8:
            continue
        out.append(p1)
    out = _merge_lists_unique(out)
    if len(out) <= 1:
        return []
    return out[:4]


def _route_name(q: str) -> str:
    t = str(q or "").lower()
    if re.search(r"\b(vs|compare|difference)\b", t) or "区别" in t or "对比" in t:
        return "compare"
    if re.search(r"\b(overview|background|define|definition)\b", t) or "是什么" in t or "介绍" in t:
        return "background"
    if re.search(r"\b(compute|calculation|calculate|formula)\b", t) or "怎么算" in t or "公式" in t:
        return "procedure"
    return "default"


def generate_query_variants(*, question: str, base_query: str, config: QueryIntelConfig) -> list[str]:
    variants: list[str] = []
    base = str(base_query or "").strip() or str(question or "").strip()
    if base:
        variants.append(base)
    kw = _keywordize(base)
    if kw and kw != base:
        variants.append(kw)
    variants.extend(_expand_abbrev(base))

    route = _route_name(base)
    use_step_back = bool(config.enable_step_back) and route in {"background", "procedure", "compare"}
    use_decomposition = bool(config.enable_decomposition) and route == "compare"

    if use_step_back:
        sb = _step_back_query(base)
        if sb and sb != base and sb != kw:
            variants.append(sb)

    if use_decomposition:
        variants.extend(_decompose(base))

    variants = _merge_lists_unique(variants)
    if not variants:
        return []
    return variants[: max(1, int(config.max_variants))]


class QueryIntelligentRetriever:
    def __init__(self, *, base_retriever: Any, config: QueryIntelConfig) -> None:
        self._base = base_retriever
        self._config = config

    def invoke(self, query: str) -> list[Document]:
        q = str(query or "").strip()
        route = _route_name(q)
        variants = generate_query_variants(question=q, base_query=q, config=self._config)
        if not variants:
            return list(self._base.invoke(q))

        ranked_lists: list[list[str]] = []
        per_variant_docs: list[list[Document]] = []
        for v in variants:
            docs = list(self._base.invoke(v))[: max(1, int(self._config.per_query_k))]
            per_variant_docs.append(docs)
            ranked_lists.append([doc_key(d) for d in docs])

        fused = rrf_scores(ranked_lists=ranked_lists, k=max(1, int(self._config.rrf_k)))
        merged: dict[str, Document] = {}
        variant_hits: dict[str, list[str]] = {}

        for v, docs in zip(variants, per_variant_docs):
            for d in docs:
                key = doc_key(d)
                if key not in merged:
                    merged[key] = d
                variant_hits.setdefault(key, [])
                variant_hits[key].append(v)

        scored: list[tuple[float, Document]] = []
        for key, d in merged.items():
            meta = dict(d.metadata or {})
            meta["query_intel_score"] = float(fused.get(key, 0.0))
            meta["query_variants"] = _merge_lists_unique(variant_hits.get(key, []))
            meta["query_route"] = route
            d.metadata = meta
            scored.append((float(meta["query_intel_score"]), d))

        scored.sort(key=lambda x: x[0], reverse=True)
        out = [d for _, d in scored][: max(1, int(self._config.final_k))]
        return out

    def debug_stats(self) -> dict[str, Any]:
        return {
            "expansion_n": int(self._config.expansion_n),
            "enable_step_back": bool(self._config.enable_step_back),
            "enable_decomposition": bool(self._config.enable_decomposition),
            "per_query_k": int(self._config.per_query_k),
            "final_k": int(self._config.final_k),
            "rrf_k": int(self._config.rrf_k),
            "max_variants": int(self._config.max_variants),
        }


def query_intel_enabled() -> bool:
    raw = os.getenv("RISKAGENT_ENABLE_QUERY_INTEL", "").lower().strip()
    if not raw:
        return False
    return raw in {"true", "1", "yes"}
