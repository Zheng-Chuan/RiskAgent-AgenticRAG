from __future__ import annotations

import os
from pathlib import Path

from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexConfig, AdvancedIndexRetriever
from riskagent_agenticrag.rag.dense_milvus_retriever import DenseMilvusRetriever, DenseMilvusRetrieverConfig
from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever
from riskagent_agenticrag.rag.query_intelligence import QueryIntelConfig, QueryIntelligentRetriever
from riskagent_agenticrag.rag.sparse_index import load_sparse_corpus


def build_retriever(*, persist_dir: Path, final_k: int = 4):
    mode = os.getenv("RISKAGENT_RETRIEVER_MODE", "step4").lower().strip()

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
    if mode in {"step1", "step2", "step3", "step4"} and not reranker_model:
        reranker_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    sparse_docs = load_sparse_corpus(persist_dir=persist_dir)
    dense_retriever = DenseMilvusRetriever(
        persist_dir=persist_dir,
        config=DenseMilvusRetrieverConfig(k=int(dense_k)),
    )
    hybrid_final_k = int(final_k)
    if mode in {"step3", "step4"}:
        hybrid_final_k = max(int(final_k), int(os.getenv("RISKAGENT_STEP3_BASE_FINAL_K", str(max(12, int(final_k) * 3)))))
    cfg = HybridConfig(
        dense_k=dense_k,
        sparse_k=sparse_k,
        candidate_k=candidate_k,
        rerank_k=rerank_k,
        final_k=int(hybrid_final_k),
        rrf_k=rrf_k,
        reranker_model=reranker_model,
        min_chunk_chars=min_chunk_chars,
        max_per_source=max_per_source,
        max_per_section=max_per_section,
    )
    base = HybridRetriever(dense_retriever=dense_retriever, sparse_docs=sparse_docs, config=cfg)
    if mode in {"hybrid", "hybrid_rerank", "step1"}:
        return base

    if mode in {"step3", "step4"}:
        adv_cfg = AdvancedIndexConfig(
            summary_k=int(os.getenv("RISKAGENT_STEP3_SUMMARY_K", "12")),
            hyde_k=int(os.getenv("RISKAGENT_STEP3_HYDE_K", "12")),
            summary_weight=float(os.getenv("RISKAGENT_STEP3_SUMMARY_WEIGHT", "0.35")),
            hyde_weight=float(os.getenv("RISKAGENT_STEP3_HYDE_WEIGHT", "0.35")),
            expand_parent=os.getenv("RISKAGENT_STEP3_EXPAND_PARENT", "true").lower().strip() in {"true", "1", "yes"},
            max_expand_chars=int(os.getenv("RISKAGENT_STEP3_MAX_EXPAND_CHARS", "1800")),
            final_k=int(final_k),
        )
        return AdvancedIndexRetriever(base_retriever=base, persist_dir=persist_dir, config=adv_cfg)

    if mode == "step2":
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

    return base
