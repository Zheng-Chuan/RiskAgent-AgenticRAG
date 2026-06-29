"""混合检索器 -- Dense (Milvus) + Sparse (BM25) + Cross-Encoder 精排."""

from __future__ import annotations

import os
import pathlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from riskagent_agenticrag.rag.utils import doc_key, rrf_scores, tokenize

# 强制离线模式
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"


def _resolve_hf_model_path(model_name: str) -> str:
    """将 HF 模型名解析为本地缓存路径, 找不到则返回原名."""
    hf_home = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    safe_name = model_name.replace("/", "--")
    snapshots_dir = hf_home / f"models--{safe_name}" / "snapshots"
    if not snapshots_dir.exists():
        return model_name
    dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
    if not dirs:
        return model_name
    return str(max(dirs, key=lambda d: d.stat().st_mtime))


def _merge_unique_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _candidate_models(*, primary: str, candidates: list[str]) -> list[str]:
    merged = list(candidates)
    if primary:
        merged.insert(0, str(primary))
    return _merge_unique_strings(merged)


def _merge_sources(doc: Document, src: str) -> None:
    """向 Document metadata 追加检索来源标记."""
    meta = doc.metadata or {}
    sources = meta.get("retrieval_sources")
    if not isinstance(sources, list):
        sources = []
    if src not in sources:
        sources.append(src)
    meta["retrieval_sources"] = sources
    doc.metadata = meta


def _compute_metadata_boost(meta: dict[str, Any], q_tokens: set[str]) -> float:
    """根据 query token 与 source/section 的匹配度计算 metadata boost."""
    if not q_tokens:
        return 0.0
    source = str(meta.get("source", "")).lower()
    section = str(meta.get("section_path", "")).lower()
    hit = 0
    for t in q_tokens:
        if t and (t in source or t in section):
            hit += 1
            if hit >= 3:
                break
    return min(0.15, 0.05 * float(hit))


@dataclass(frozen=True)
class HybridConfig:
    dense_k: int = 30
    sparse_k: int = 30
    candidate_k: int = 50
    rerank_k: int = 50
    final_k: int = 4
    rrf_k: int = 60
    reranker_model: str = ""
    reranker_candidates: tuple[str, ...] = ()
    min_chunk_chars: int = 80
    max_per_source: int = 2
    max_per_section: int = 1


class HybridRetriever:
    """Dense + Sparse 混合检索, 支持 RRF 融合 / Cross-Encoder 精排 / MMR 多样性."""

    def __init__(
        self,
        *,
        dense_retriever: Any,
        sparse_docs: list[Document],
        config: HybridConfig,
    ) -> None:
        self._dense = dense_retriever
        self._sparse_docs = sparse_docs
        self._cfg = config
        self._bm25 = None
        self._bm25_keys: list[str] = []
        self._reranker = None
        self._requested_reranker_model = str(config.reranker_model or "").strip()
        self._reranker_candidates = _candidate_models(
            primary=self._requested_reranker_model,
            candidates=[str(x) for x in config.reranker_candidates],
        )
        self._active_reranker_model = ""
        self._reranker_status = "disabled"
        self._reranker_init_errors: list[str] = []

        if sparse_docs:
            tokens = [tokenize(d.page_content or "") for d in sparse_docs]
            self._bm25 = BM25Okapi(tokens)
            self._bm25_keys = [doc_key(d) for d in sparse_docs]

        if self._reranker_candidates:
            self._init_reranker()

    def _init_reranker(self) -> None:
        last_error = ""
        for idx, model_name in enumerate(self._reranker_candidates):
            local_path = _resolve_hf_model_path(model_name)
            try:
                self._reranker = CrossEncoder(local_path, local_files_only=True, trust_remote_code=True)
                self._active_reranker_model = model_name
                if idx == 0:
                    self._reranker_status = "enabled"
                else:
                    self._reranker_status = "fallback_enabled"
                return
            except Exception as exc:
                last_error = f"{model_name}: {type(exc).__name__}"
                self._reranker_init_errors.append(last_error)
        self._reranker = None
        self._reranker_status = "unavailable" if last_error else "disabled"

    # ---- 内部方法 ----

    def _sparse_query(self, query: str) -> str:
        """去重 query token, 用于 BM25 查询."""
        toks = tokenize(query)
        seen: set[str] = set()
        uniq: list[str] = []
        for t in toks:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return " ".join(uniq[:24])

    def _passes_filter(self, d: Document) -> bool:
        """过滤低质量 chunk (太短 / 非文本 / 目录页)."""
        text = (d.page_content or "").strip()
        if len(text) < self._cfg.min_chunk_chars:
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
        """MMR 多样性选择: 限制每个 source / section 的最大数量."""
        picked: list[Document] = []
        per_source: dict[str, int] = defaultdict(int)
        per_section: dict[str, int] = defaultdict(int)
        max_src = max(1, self._cfg.max_per_source)
        max_sec = max(1, self._cfg.max_per_section)

        for d in docs:
            meta = d.metadata or {}
            source = str(meta.get("source", "")).strip()
            section = str(meta.get("section_path", "")).strip()
            if source and per_source[source] >= max_src:
                continue
            if section and per_section[section] >= max_sec:
                continue
            picked.append(d)
            if source:
                per_source[source] += 1
            if section:
                per_section[section] += 1
            if len(picked) >= self._cfg.final_k:
                return picked

        # 不够则补充
        for d in docs:
            if len(picked) >= self._cfg.final_k:
                break
            if d not in picked:
                picked.append(d)
        return picked[:self._cfg.final_k]

    def _coarse_score(self, d: Document) -> float:
        meta = d.metadata or {}
        return float(meta.get("rrf_score", 0.0)) + 0.5 * float(meta.get("bm25_score", 0.0)) + float(meta.get("metadata_boost", 0.0))

    # ---- 主检索流程 ----

    def invoke(self, query: str) -> list[Document]:
        q = str(query or "").strip()
        q_tokens = set(tokenize(q))

        # 1) Dense 召回
        dense_docs: list[Document] = list(self._dense.invoke(q))[:max(1, self._cfg.dense_k)]

        # 2) Sparse (BM25) 召回
        sparse_docs: list[Document] = []
        bm25_norm: dict[str, float] = {}
        bm25_rank: dict[str, int] = {}
        if self._bm25 is not None and self._sparse_docs:
            q_toks = tokenize(self._sparse_query(q))
            scores = self._bm25.get_scores(q_toks)
            top_idx = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[:max(1, self._cfg.sparse_k)]
            sparse_docs = [self._sparse_docs[i] for i in top_idx]
            max_s = float(max((float(scores[i]) for i in top_idx), default=0.0))
            denom = max_s if max_s > 0 else 1.0
            for rank_pos, i in enumerate(top_idx, start=1):
                key = self._bm25_keys[i] if i < len(self._bm25_keys) else ""
                if key:
                    bm25_norm[key] = float(scores[i]) / denom
                    bm25_rank[key] = rank_pos

        # 3) RRF 融合
        dense_keys = [doc_key(d) for d in dense_docs]
        sparse_keys = [doc_key(d) for d in sparse_docs]
        dense_rank_map = {k: i + 1 for i, k in enumerate(dense_keys)}
        sparse_rank_map = {k: i + 1 for i, k in enumerate(sparse_keys)}
        rrf = rrf_scores(ranked_lists=[dense_keys, sparse_keys], k=self._cfg.rrf_k)

        # 4) 合并 dense + sparse, 计算 metadata_boost
        merged: dict[str, Document] = {}
        for src_label, docs, rank_map in [("dense", dense_docs, dense_rank_map), ("sparse", sparse_docs, sparse_rank_map)]:
            for d in docs:
                key = doc_key(d)
                if key not in merged:
                    merged[key] = Document(page_content=d.page_content, metadata=dict(d.metadata or {}))
                _merge_sources(merged[key], src_label)
                meta = merged[key].metadata
                meta[f"{src_label}_rank"] = rank_map.get(key, 0)
                meta["rrf_score"] = float(rrf.get(key, 0.0))
                if src_label == "sparse":
                    meta["bm25_score"] = float(bm25_norm.get(key, 0.0))
                    meta["bm25_rank"] = bm25_rank.get(key, 0)
                boost = _compute_metadata_boost(meta, q_tokens)
                meta["metadata_boost"] = max(float(meta.get("metadata_boost", 0.0)), boost)

        # 5) 过滤 + 粗排
        filtered = [d for d in merged.values() if self._passes_filter(d)]
        candidates = sorted(filtered, key=lambda d: float((d.metadata or {}).get("rrf_score", 0.0)), reverse=True)[:max(1, self._cfg.candidate_k)]
        for d in candidates:
            d.metadata["coarse_score"] = self._coarse_score(d)
        coarse_sorted = sorted(candidates, key=lambda d: float(d.metadata.get("coarse_score", 0.0)), reverse=True)
        rerank_pool = coarse_sorted[:max(1, self._cfg.rerank_k)]

        # 6) Cross-Encoder 精排 (可选)
        if self._reranker is None:
            self._set_confidence_gap(rerank_pool, "coarse_score")
            return self._diversity_select(rerank_pool)

        pairs = [(q, d.page_content or "") for d in rerank_pool]
        ce_scores = self._reranker.predict(pairs)
        for s, d in zip(ce_scores, rerank_pool):
            d.metadata["rerank_score"] = float(s)
            d.metadata["reranker_model"] = self._active_reranker_model
        rerank_pool.sort(key=lambda d: float(d.metadata.get("rerank_score", 0.0)), reverse=True)
        self._set_confidence_gap(rerank_pool, "rerank_score")
        return self._diversity_select(rerank_pool)

    @staticmethod
    def _set_confidence_gap(docs: list[Document], score_key: str) -> None:
        if not docs:
            return
        top1 = float(docs[0].metadata.get(score_key, 0.0))
        for d in docs:
            d.metadata["confidence_gap_to_top1"] = top1 - float(d.metadata.get(score_key, 0.0))

    def debug_stats(self) -> dict[str, Any]:
        return {
            "sparse_docs": len(self._sparse_docs),
            "has_bm25": self._bm25 is not None,
            "reranker_model": self._requested_reranker_model,
            "reranker_candidates": list(self._reranker_candidates),
            "active_reranker_model": self._active_reranker_model,
            "reranker_status": self._reranker_status,
            "reranker_init_errors": list(self._reranker_init_errors),
            "dense_k": self._cfg.dense_k,
            "sparse_k": self._cfg.sparse_k,
            "candidate_k": self._cfg.candidate_k,
            "rerank_k": self._cfg.rerank_k,
            "final_k": self._cfg.final_k,
            "rrf_k": self._cfg.rrf_k,
            "min_chunk_chars": self._cfg.min_chunk_chars,
            "max_per_source": self._cfg.max_per_source,
            "max_per_section": self._cfg.max_per_section,
        }
