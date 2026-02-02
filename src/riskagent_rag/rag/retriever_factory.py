from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from riskagent_rag.rag.hybrid_retriever import HybridConfig, HybridRetriever
from riskagent_rag.rag.query_intelligence import QueryIntelConfig, QueryIntelligentRetriever
from riskagent_rag.rag.sparse_index import load_sparse_corpus


def build_retriever(*, vectorstore: Any, persist_dir: Path, final_k: int = 4) -> Any:
    mode = os.getenv("RISKAGENT_RETRIEVER_MODE", "vector").lower().strip()
    if mode not in {"hybrid", "hybrid_rerank", "step1", "step2"}:
        return vectorstore.as_retriever(search_kwargs={"k": int(final_k)})

    dense_k = int(os.getenv("RISKAGENT_DENSE_K", "30"))
    sparse_k = int(os.getenv("RISKAGENT_SPARSE_K", "30"))
    candidate_k = int(os.getenv("RISKAGENT_CANDIDATE_K", "50"))
    rerank_k = int(os.getenv("RISKAGENT_RERANK_K", str(candidate_k)))
    rrf_k = int(os.getenv("RISKAGENT_RRF_K", "60"))
    min_chunk_chars = int(os.getenv("RISKAGENT_MIN_CHUNK_CHARS", "80"))
    max_per_source = int(os.getenv("RISKAGENT_MAX_PER_SOURCE", "2"))
    max_per_section = int(os.getenv("RISKAGENT_MAX_PER_SECTION", "1"))
    reranker_model = os.getenv("RISKAGENT_RERANKER_MODEL", "").strip()
    if mode == "hybrid":
        reranker_model = ""
    if mode in {"step1", "step2"} and not reranker_model:
        reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    sparse_docs = load_sparse_corpus(persist_dir=persist_dir)
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": int(dense_k)})
    cfg = HybridConfig(
        dense_k=dense_k,
        sparse_k=sparse_k,
        candidate_k=candidate_k,
        rerank_k=rerank_k,
        final_k=int(final_k),
        rrf_k=rrf_k,
        reranker_model=reranker_model,
        min_chunk_chars=min_chunk_chars,
        max_per_source=max_per_source,
        max_per_section=max_per_section,
    )
    base = HybridRetriever(dense_retriever=dense_retriever, sparse_docs=sparse_docs, config=cfg)
    if mode != "step2":
        return base

    qi_cfg = QueryIntelConfig(
        expansion_n=int(os.getenv("RISKAGENT_QUERY_EXPANSION_N", "3")),
        enable_step_back=os.getenv("RISKAGENT_ENABLE_STEP_BACK", "true").lower().strip() in {"true", "1", "yes"},
        enable_decomposition=os.getenv("RISKAGENT_ENABLE_DECOMPOSITION", "true").lower().strip() in {"true", "1", "yes"},
        per_query_k=int(os.getenv("RISKAGENT_PER_QUERY_K", str(max(4, dense_k // 2)))),
        final_k=int(final_k),
        rrf_k=int(os.getenv("RISKAGENT_QUERY_RRF_K", "60")),
        max_variants=int(os.getenv("RISKAGENT_QUERY_MAX_VARIANTS", "8")),
    )
    return QueryIntelligentRetriever(base_retriever=base, config=qi_cfg)
