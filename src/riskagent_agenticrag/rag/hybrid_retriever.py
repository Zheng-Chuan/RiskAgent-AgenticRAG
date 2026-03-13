from __future__ import annotations

import os

# Force offline mode BEFORE any HuggingFace imports
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

import pathlib
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document  # type: ignore[import-not-found]
from rank_bm25 import BM25Okapi  # type: ignore[import-not-found]
from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]


def _resolve_hf_model_path(model_name: str) -> str:
    """Resolve HuggingFace model name to local cache path.
    
    If the model is cached locally, return the absolute path to the snapshot.
    Otherwise, return the original model name.
    """
    # Default HuggingFace cache location
    hf_home = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    
    # Convert model name to cache directory format
    # e.g., "cross-encoder/ms-marco-MiniLM-L-6-v2" -> "models--cross-encoder--ms-marco-MiniLM-L-6-v2"
    safe_name = model_name.replace("/", "--")
    cache_dir = hf_home / f"models--{safe_name}"
    
    if not cache_dir.exists():
        return model_name
    
    # Find the snapshots directory
    snapshots_dir = cache_dir / "snapshots"
    if not snapshots_dir.exists():
        return model_name
    
    # Get the first (and usually only) snapshot
    snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
    if not snapshot_dirs:
        return model_name
    
    # Return the path to the latest snapshot
    latest_snapshot = max(snapshot_dirs, key=lambda d: d.stat().st_mtime)
    return str(latest_snapshot)


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


def _rrf_scores(*, ranked_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, key in enumerate(ranked):
            scores[key] = scores.get(key, 0.0) + 1.0 / float(k + rank + 1)
    return scores


def _doc_key(d: Document) -> str:
    meta = d.metadata or {}
    chunk_id = str(meta.get("chunk_id", "")).strip()
    source = str(meta.get("source", "")).strip()
    if chunk_id and source:
        return f"{source}::{chunk_id}"
    if chunk_id:
        return f"chunk::{chunk_id}"
    if source:
        return f"source::{source}::{hash(d.page_content or '')}"
    return f"raw::{hash(d.page_content or '')}"


def _merge_sources(existing: Document, src: str) -> None:
    meta = existing.metadata or {}
    sources = meta.get("retrieval_sources")
    if not isinstance(sources, list):
        sources = []
    if src not in sources:
        sources.append(src)
    meta["retrieval_sources"] = sources
    existing.metadata = meta


@dataclass(frozen=True)
class HybridConfig:
    dense_k: int = 30
    sparse_k: int = 30
    candidate_k: int = 50
    rerank_k: int = 50
    final_k: int = 4
    rrf_k: int = 60
    reranker_model: str = ""
    min_chunk_chars: int = 80
    max_per_source: int = 2
    max_per_section: int = 1


class HybridRetriever:
    def __init__(
        self,
        *,
        dense_retriever: Any,
        sparse_docs: list[Document],
        config: HybridConfig,
    ) -> None:
        self._dense_retriever = dense_retriever
        self._sparse_docs = sparse_docs
        self._config = config
        self._bm25 = None
        self._bm25_keys: list[str] = []
        self._reranker = None

        if sparse_docs:
            tokens = [_tokenize(d.page_content or "") for d in sparse_docs]
            self._bm25 = BM25Okapi(tokens)
            self._bm25_keys = [_doc_key(d) for d in sparse_docs]

        if config.reranker_model:
            # Resolve to local cache path and use local_files_only
            # to force using cached model (no HuggingFace connection)
            local_model_path = _resolve_hf_model_path(config.reranker_model)
            self._reranker = CrossEncoder(
                local_model_path,
                local_files_only=True,
                trust_remote_code=True
            )

    def _query_aware_sparse_query(self, query: str) -> str:
        toks = _tokenize(query)
        if not toks:
            return str(query or "")
        uniq: list[str] = []
        seen: set[str] = set()
        for t in toks:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
        return " ".join(uniq[:24])

    def _passes_citation_filter(self, d: Document) -> bool:
        text = (d.page_content or "").strip()
        if len(text) < int(self._config.min_chunk_chars):
            return False
        alnum = sum(1 for ch in text if ch.isalnum())
        if alnum < max(10, int(len(text) * 0.15)):
            return False
        lowered = text.lower()
        if "table of contents" in lowered:
            return False
        if "business portal" in lowered and "wikipedia" in lowered:
            return False
        return True

    def _diversity_select(self, docs: list[Document]) -> list[Document]:
        picked: list[Document] = []
        per_source: dict[str, int] = defaultdict(int)
        per_section: dict[str, int] = defaultdict(int)
        max_per_source = max(1, int(self._config.max_per_source))
        max_per_section = max(1, int(self._config.max_per_section))

        for d in docs:
            meta = d.metadata or {}
            source = str(meta.get("source", "")).strip()
            section = str(meta.get("section_path", "")).strip()

            if source and per_source[source] >= max_per_source:
                continue
            if section and per_section[section] >= max_per_section:
                continue

            picked.append(d)
            if source:
                per_source[source] += 1
            if section:
                per_section[section] += 1
            if len(picked) >= int(self._config.final_k):
                return picked

        for d in docs:
            if len(picked) >= int(self._config.final_k):
                break
            if d in picked:
                continue
            picked.append(d)

        return picked[: int(self._config.final_k)]

    def _coarse_score(self, d: Document) -> float:
        meta = d.metadata or {}
        rrf = float(meta.get("rrf_score", 0.0))
        bm25 = float(meta.get("bm25_score", 0.0))
        boost = float(meta.get("metadata_boost", 0.0))
        return rrf + 0.5 * bm25 + boost

    def invoke(self, query: str) -> list[Document]:
        q = str(query or "").strip()
        q_tokens_set = set(_tokenize(q))
        dense_docs: list[Document] = list(self._dense_retriever.invoke(q))[: max(1, int(self._config.dense_k))]

        sparse_docs: list[Document] = []
        bm25_score_norm: dict[str, float] = {}
        bm25_rank: dict[str, int] = {}
        if self._bm25 is not None and self._sparse_docs:
            sparse_query = self._query_aware_sparse_query(q)
            q_tokens = _tokenize(sparse_query)
            scores = self._bm25.get_scores(q_tokens)
            top_idx = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[: max(1, int(self._config.sparse_k))]
            sparse_docs = [self._sparse_docs[i] for i in top_idx]
            max_score = float(max([float(scores[i]) for i in top_idx], default=0.0))
            denom = max_score if max_score > 0 else 1.0
            for rank_pos, i in enumerate(top_idx, start=1):
                key = self._bm25_keys[i] if i < len(self._bm25_keys) else ""
                if not key:
                    continue
                bm25_score_norm[key] = float(scores[i]) / denom
                bm25_rank[key] = int(rank_pos)

        merged: dict[str, Document] = {}
        dense_rank = [_doc_key(d) for d in dense_docs]
        sparse_rank = [_doc_key(d) for d in sparse_docs]
        dense_rank_map = {k: i + 1 for i, k in enumerate(dense_rank)}
        sparse_rank_map = {k: i + 1 for i, k in enumerate(sparse_rank)}
        rrf = _rrf_scores(ranked_lists=[dense_rank, sparse_rank], k=int(self._config.rrf_k))

        for d in dense_docs:
            key = _doc_key(d)
            if key not in merged:
                merged[key] = Document(page_content=d.page_content, metadata=dict(d.metadata or {}))
            _merge_sources(merged[key], "dense")
            meta = merged[key].metadata or {}
            meta["dense_rank"] = int(dense_rank_map.get(key, 0))
            merged[key].metadata["rrf_score"] = float(rrf.get(key, 0.0))
            source = str(meta.get("source", "")).lower()
            section = str(meta.get("section_path", "")).lower()
            boost = 0.0
            if q_tokens_set:
                hit = 0
                for t in q_tokens_set:
                    if t and (t in source or t in section):
                        hit += 1
                        if hit >= 3:
                            break
                boost = min(0.15, 0.05 * float(hit))
            meta["metadata_boost"] = float(max(float(meta.get("metadata_boost", 0.0)), boost))
            merged[key].metadata = meta

        for d in sparse_docs:
            key = _doc_key(d)
            if key not in merged:
                merged[key] = Document(page_content=d.page_content, metadata=dict(d.metadata or {}))
            _merge_sources(merged[key], "sparse")
            meta = merged[key].metadata or {}
            meta["sparse_rank"] = int(sparse_rank_map.get(key, 0))
            merged[key].metadata["rrf_score"] = float(rrf.get(key, 0.0))
            meta["bm25_score"] = float(bm25_score_norm.get(key, 0.0))
            meta["bm25_rank"] = int(bm25_rank.get(key, 0))
            source = str(meta.get("source", "")).lower()
            section = str(meta.get("section_path", "")).lower()
            boost = 0.0
            if q_tokens_set:
                hit = 0
                for t in q_tokens_set:
                    if t and (t in source or t in section):
                        hit += 1
                        if hit >= 3:
                            break
                boost = min(0.15, 0.05 * float(hit))
            meta["metadata_boost"] = float(max(float(meta.get("metadata_boost", 0.0)), boost))
            merged[key].metadata = meta

        filtered = [d for d in merged.values() if self._passes_citation_filter(d)]
        candidates = sorted(filtered, key=lambda d: float((d.metadata or {}).get("rrf_score", 0.0)), reverse=True)[
            : max(1, int(self._config.candidate_k))
        ]

        for d in candidates:
            meta = d.metadata or {}
            meta["coarse_score"] = float(self._coarse_score(d))
            d.metadata = meta
        coarse_sorted = sorted(candidates, key=lambda d: float((d.metadata or {}).get("coarse_score", 0.0)), reverse=True)
        rerank_candidates = coarse_sorted[: max(1, int(self._config.rerank_k))]

        if self._reranker is None:
            if rerank_candidates:
                top1 = float((rerank_candidates[0].metadata or {}).get("coarse_score", 0.0))
                for d in rerank_candidates:
                    meta = d.metadata or {}
                    score = float(meta.get("coarse_score", 0.0))
                    meta["confidence_gap_to_top1"] = float(top1 - score)
                    d.metadata = meta
            return self._diversity_select(rerank_candidates)

        pairs: list[tuple[str, str]] = [(q, d.page_content or "") for d in rerank_candidates]
        scores = self._reranker.predict(pairs)
        scored: list[tuple[float, Document]] = []
        for s, d in zip(scores, rerank_candidates):
            meta = d.metadata or {}
            meta["rerank_score"] = float(s)
            d.metadata = meta
            scored.append((float(s), d))

        scored.sort(key=lambda x: x[0], reverse=True)
        reranked = [d for _, d in scored]
        reranked.sort(key=lambda d: float((d.metadata or {}).get("rerank_score", 0.0)), reverse=True)
        if reranked:
            top1 = float((reranked[0].metadata or {}).get("rerank_score", 0.0))
            for d in reranked:
                meta = d.metadata or {}
                score = float(meta.get("rerank_score", 0.0))
                meta["confidence_gap_to_top1"] = float(top1 - score)
                d.metadata = meta
        return self._diversity_select(reranked)

    def debug_stats(self) -> dict[str, Any]:
        return {
            "sparse_docs": len(self._sparse_docs),
            "has_bm25": self._bm25 is not None,
            "reranker_model": self._config.reranker_model or "",
            "dense_k": self._config.dense_k,
            "sparse_k": self._config.sparse_k,
            "candidate_k": self._config.candidate_k,
            "rerank_k": self._config.rerank_k,
            "final_k": self._config.final_k,
            "rrf_k": self._config.rrf_k,
            "min_chunk_chars": self._config.min_chunk_chars,
            "max_per_source": self._config.max_per_source,
            "max_per_section": self._config.max_per_section,
        }
