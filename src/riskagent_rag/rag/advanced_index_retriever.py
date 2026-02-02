from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]
from rank_bm25 import BM25Okapi  # type: ignore[import-not-found]

from riskagent_rag.rag.advanced_index import load_hyde_corpus, load_summary_corpus, parent_corpus_by_id


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(str(text or ""))]


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
            self._summary_bm25 = BM25Okapi([_tokenize(d.page_content or "") for d in summary_docs])

        hyde_docs = load_hyde_corpus(persist_dir=persist_dir)
        self._hyde_docs = hyde_docs
        self._hyde_bm25 = None
        if hyde_docs:
            self._hyde_bm25 = BM25Okapi([_tokenize(d.page_content or "") for d in hyde_docs])

    def _parent_score_map(self, *, bm25: BM25Okapi | None, docs: list[Document], query: str, k: int) -> dict[str, float]:
        if bm25 is None or not docs:
            return {}
        toks = _tokenize(query)
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
        for d in base_docs:
            meta = dict(d.metadata or {})
            pid = str(meta.get("parent_id") or "").strip()
            base_score = _best_base_score(d)
            s_score = float(summary_map.get(pid, 0.0)) if pid else 0.0
            h_score = float(hyde_map.get(pid, 0.0)) if pid else 0.0
            adv = float(base_score) + float(self._config.summary_weight) * s_score + float(self._config.hyde_weight) * h_score
            meta["summary_score"] = float(s_score)
            meta["hyde_score"] = float(h_score)
            meta["advanced_index_score"] = float(adv)

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
                parent = self._parent_by_id[pid]
                expanded = str(parent.page_content or "").strip()
                if expanded:
                    meta["expanded_text"] = expanded[: int(self._config.max_expand_chars)]
                    meta["expanded_len"] = int(len(meta["expanded_text"]))
                    meta["parent_type"] = str((parent.metadata or {}).get("parent_type") or "")
            d.metadata = meta
            scored.append((adv, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored][: max(1, int(self._config.final_k))]

    def debug_stats(self) -> dict[str, Any]:
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
        }

