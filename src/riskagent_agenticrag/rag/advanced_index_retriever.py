"""高级索引检索器 -- Summary/HyDE BM25 加权 + Parent 展开."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from riskagent_agenticrag.rag.advanced_index import load_hyde_corpus, load_summary_corpus, parent_corpus_by_id
from riskagent_agenticrag.rag.query_intelligence import _route_name
from riskagent_agenticrag.rag.self_rag import should_require_numeric_backing
from riskagent_agenticrag.rag.utils import tokenize


def _normalize(scores: list[float], idxs: list[int]) -> dict[int, float]:
    if not idxs:
        return {}
    max_score = float(max([float(scores[i]) for i in idxs], default=0.0))
    denom = max_score if max_score > 0 else 1.0
    out: dict[int, float] = {}
    for i in idxs:
        out[int(i)] = float(scores[i]) / denom
    return out


def _best_base_score(d: Document) -> float:
    meta = d.metadata or {}
    for k in ("rerank_score", "coarse_score", "rrf_score"):
        v = meta.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


@dataclass(frozen=True)
class AdvancedIndexConfig:
    summary_k: int = 12
    hyde_k: int = 12
    summary_weight: float = 0.35
    hyde_weight: float = 0.35
    expand_parent: bool = True
    max_expand_chars: int = 1800
    final_k: int = 4


@dataclass(frozen=True)
class ParentExpandPolicy:
    route: str
    max_docs: int
    max_chars: int
    min_parent_signal: float
    max_gap_to_top1: float
    short_chunk_chars: int


class AdvancedIndexRetriever:
    def __init__(
        self,
        *,
        base_retriever: Any,
        persist_dir: Any,
        config: AdvancedIndexConfig,
    ) -> None:
        self._base = base_retriever
        self._persist_dir = persist_dir
        self._config = config

        self._parent_by_id = parent_corpus_by_id(persist_dir=persist_dir)

        summary_docs = load_summary_corpus(persist_dir=persist_dir)
        self._summary_docs = summary_docs
        self._summary_bm25 = None
        if summary_docs:
            self._summary_bm25 = BM25Okapi([tokenize(d.page_content or "") for d in summary_docs])

        hyde_docs = load_hyde_corpus(persist_dir=persist_dir)
        self._hyde_docs = hyde_docs
        self._hyde_bm25 = None
        if hyde_docs:
            self._hyde_bm25 = BM25Okapi([tokenize(d.page_content or "") for d in hyde_docs])

    @staticmethod
    def _query_route(*, query: str, docs: list[Document]) -> str:
        if should_require_numeric_backing(question=query):
            return "numeric"
        for d in docs:
            meta = d.metadata or {}
            route = str(meta.get("query_route") or "").strip()
            if route:
                return route
        return _route_name(query)

    def _expand_policy(self, *, route: str) -> ParentExpandPolicy:
        max_chars = max(200, int(self._config.max_expand_chars))
        policies = {
            "compare": ParentExpandPolicy(
                route="compare",
                max_docs=min(max(1, int(self._config.final_k)), 3),
                max_chars=max_chars,
                min_parent_signal=0.0,
                max_gap_to_top1=0.45,
                short_chunk_chars=520,
            ),
            "background": ParentExpandPolicy(
                route="background",
                max_docs=min(max(1, int(self._config.final_k)), 2),
                max_chars=min(max_chars, 1600),
                min_parent_signal=0.0,
                max_gap_to_top1=0.35,
                short_chunk_chars=420,
            ),
            "procedure": ParentExpandPolicy(
                route="procedure",
                max_docs=min(max(1, int(self._config.final_k)), 2),
                max_chars=min(max_chars, 1400),
                min_parent_signal=0.0,
                max_gap_to_top1=0.30,
                short_chunk_chars=360,
            ),
            "numeric": ParentExpandPolicy(
                route="numeric",
                max_docs=1,
                max_chars=min(max_chars, 700),
                min_parent_signal=0.30,
                max_gap_to_top1=0.12,
                short_chunk_chars=260,
            ),
            "default": ParentExpandPolicy(
                route="default",
                max_docs=1,
                max_chars=min(max_chars, 900),
                min_parent_signal=0.20,
                max_gap_to_top1=0.15,
                short_chunk_chars=260,
            ),
        }
        return policies.get(route, policies["default"])

    @staticmethod
    def _expand_reason(
        *,
        route: str,
        rank_idx: int,
        chunk_len: int,
        parent_signal: float,
        gap_to_top1: float,
        policy: ParentExpandPolicy,
    ) -> str:
        if rank_idx >= int(policy.max_docs):
            return ""
        if float(policy.min_parent_signal) > 0:
            strong_signal = float(parent_signal) >= float(policy.min_parent_signal)
        else:
            strong_signal = float(parent_signal) > 0.0
        near_top = float(gap_to_top1) <= float(policy.max_gap_to_top1)
        short_chunk = int(chunk_len) <= int(policy.short_chunk_chars)

        if route in {"compare", "background", "procedure"}:
            if strong_signal:
                return "parent_signal"
            if near_top:
                return "near_top"
            if short_chunk:
                return "short_chunk"
            return ""

        if route == "numeric":
            if strong_signal and near_top and short_chunk:
                return "numeric_backing"
            return ""

        if strong_signal and near_top:
            return "default_signal"
        if near_top and short_chunk:
            return "default_short_chunk"
        return ""

    def _parent_score_map(self, *, bm25: BM25Okapi | None, docs: list[Document], query: str, k: int) -> dict[str, float]:
        if bm25 is None or not docs:
            return {}
        toks = tokenize(query)
        if not toks:
            return {}
        scores = bm25.get_scores(toks)
        idxs = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[: max(1, int(k))]
        norm = _normalize(list(scores), idxs)
        out: dict[str, float] = {}
        for i in idxs:
            pid = str((docs[i].metadata or {}).get("parent_id") or "").strip()
            if not pid:
                continue
            out[pid] = float(norm.get(int(i), 0.0))
        return out

    def invoke(self, query: str) -> list[Document]:
        q = str(query or "").strip()
        base_docs: list[Document] = list(self._base.invoke(q))
        if not base_docs:
            return []
        route = self._query_route(query=q, docs=base_docs)
        expand_policy = self._expand_policy(route=route)

        summary_map = self._parent_score_map(
            bm25=self._summary_bm25,
            docs=self._summary_docs,
            query=q,
            k=int(self._config.summary_k),
        )
        hyde_map = self._parent_score_map(
            bm25=self._hyde_bm25,
            docs=self._hyde_docs,
            query=q,
            k=int(self._config.hyde_k),
        )

        scored: list[tuple[float, Document]] = []
        for rank_idx, d in enumerate(base_docs):
            meta = dict(d.metadata or {})
            pid = str(meta.get("parent_id") or "").strip()
            base_score = _best_base_score(d)
            s_score = float(summary_map.get(pid, 0.0)) if pid else 0.0
            h_score = float(hyde_map.get(pid, 0.0)) if pid else 0.0
            parent_signal = max(s_score, h_score)
            adv = float(base_score) + float(self._config.summary_weight) * s_score + float(self._config.hyde_weight) * h_score
            meta["summary_score"] = float(s_score)
            meta["hyde_score"] = float(h_score)
            meta["advanced_index_score"] = float(adv)
            meta["expand_parent_route"] = route
            meta["expand_parent_applied"] = False
            meta["expand_parent_signal"] = float(parent_signal)

            sources = meta.get("indexing_sources")
            if not isinstance(sources, list):
                sources = []
            sources.append("child_vector")
            if s_score > 0:
                sources.append("summary_bm25")
            if h_score > 0:
                sources.append("hyde_bm25")
            meta["indexing_sources"] = list(dict.fromkeys([str(x) for x in sources if str(x or "").strip()]))

            if self._config.expand_parent and pid and pid in self._parent_by_id:
                gap_to_top1 = float(meta.get("confidence_gap_to_top1", 1.0))
                reason = self._expand_reason(
                    route=route,
                    rank_idx=rank_idx,
                    chunk_len=len(d.page_content or ""),
                    parent_signal=parent_signal,
                    gap_to_top1=gap_to_top1,
                    policy=expand_policy,
                )
                parent = self._parent_by_id[pid]
                expanded = str(parent.page_content or "").strip()
                if expanded and reason:
                    meta["expanded_text"] = expanded[: int(expand_policy.max_chars)]
                    meta["expanded_len"] = int(len(meta["expanded_text"]))
                    meta["parent_type"] = str((parent.metadata or {}).get("parent_type") or "")
                    meta["expand_parent_applied"] = True
                    meta["expand_parent_reason"] = reason
                    meta["indexing_sources"] = list(dict.fromkeys(meta["indexing_sources"] + ["parent_expand"]))
            d.metadata = meta
            scored.append((adv, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored][: max(1, int(self._config.final_k))]

    def debug_stats(self) -> dict[str, Any]:
        base_debug = {}
        if hasattr(self._base, "debug_stats"):
            try:
                base_debug = dict(self._base.debug_stats() or {})
            except Exception:
                base_debug = {}
        return {
            "parents": int(len(self._parent_by_id)),
            "summaries": int(len(self._summary_docs)),
            "hydes": int(len(self._hyde_docs)),
            "summary_k": int(self._config.summary_k),
            "hyde_k": int(self._config.hyde_k),
            "summary_weight": float(self._config.summary_weight),
            "hyde_weight": float(self._config.hyde_weight),
            "expand_parent": bool(self._config.expand_parent),
            "max_expand_chars": int(self._config.max_expand_chars),
            "final_k": int(self._config.final_k),
            "expand_policies": {
                route: self._expand_policy(route=route).__dict__
                for route in ("compare", "background", "procedure", "numeric", "default")
            },
            "base_debug": base_debug,
        }
