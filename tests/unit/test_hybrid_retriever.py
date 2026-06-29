from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


@pytest.mark.unit
def test_hybrid_retriever_falls_back_to_second_reranker_candidate():
    from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever

    long_text = "Basel market risk capital rule " * 20
    dense = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content=long_text,
                    metadata={"chunk_id": "c1", "source": "a.md", "section_path": "sec/a"},
                )
            ]
        )
    )
    fake_reranker = MagicMock(predict=MagicMock(return_value=[0.9]))

    def _fake_cross_encoder(model_name: str, **_kwargs):
        if model_name == "bad/model":
            raise OSError("missing model")
        return fake_reranker

    with patch("riskagent_agenticrag.rag.hybrid_retriever.CrossEncoder", side_effect=_fake_cross_encoder):
        retriever = HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(
                dense_k=4,
                sparse_k=4,
                candidate_k=4,
                rerank_k=4,
                final_k=2,
                reranker_model="bad/model",
                reranker_candidates=("bad/model", "good/model"),
            ),
        )
        docs = retriever.invoke("Basel market risk capital")

    assert len(docs) == 1
    assert docs[0].metadata["reranker_model"] == "good/model"
    debug = retriever.debug_stats()
    assert debug["active_reranker_model"] == "good/model"
    assert debug["reranker_status"] == "fallback_enabled"
    assert debug["reranker_init_errors"] == ["bad/model: OSError"]


@pytest.mark.unit
def test_hybrid_retriever_reports_unavailable_when_all_candidates_fail():
    from riskagent_agenticrag.rag.hybrid_retriever import HybridConfig, HybridRetriever

    long_text = "Basel market risk capital rule " * 20
    dense = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content=long_text,
                    metadata={"chunk_id": "c1", "source": "a.md", "section_path": "sec/a"},
                )
            ]
        )
    )

    with patch("riskagent_agenticrag.rag.hybrid_retriever.CrossEncoder", side_effect=OSError("missing model")):
        retriever = HybridRetriever(
            dense_retriever=dense,
            sparse_docs=[],
            config=HybridConfig(
                dense_k=4,
                sparse_k=4,
                candidate_k=4,
                rerank_k=4,
                final_k=2,
                reranker_model="bad/model",
                reranker_candidates=("bad/model", "bad/second"),
            ),
        )
        docs = retriever.invoke("Basel market risk capital")

    assert len(docs) == 1
    assert "rerank_score" not in (docs[0].metadata or {})
    debug = retriever.debug_stats()
    assert debug["active_reranker_model"] == ""
    assert debug["reranker_status"] == "unavailable"
    assert debug["reranker_init_errors"] == [
        "bad/model: OSError",
        "bad/second: OSError",
    ]
