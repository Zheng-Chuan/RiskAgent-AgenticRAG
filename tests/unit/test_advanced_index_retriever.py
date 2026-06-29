from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_default_route_does_not_expand_without_parent_signal(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexConfig, AdvancedIndexRetriever

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="parent context " * 200, metadata={"parent_id": "p1", "parent_type": "section"})
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="desk requirements " * 30,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "default",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.05,
                    },
                )
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    docs = retriever.invoke("FRTB desk requirements")

    assert len(docs) == 1
    meta = docs[0].metadata or {}
    assert meta["expand_parent_route"] == "default"
    assert meta["expand_parent_applied"] is False
    assert "expanded_text" not in meta
    assert "parent_expand" not in (meta.get("indexing_sources") or [])


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_default_route_expands_when_parent_signal_is_strong(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexConfig, AdvancedIndexRetriever

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="parent context " * 200, metadata={"parent_id": "p1", "parent_type": "section"})
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="desk requirements " * 20,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "default",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.05,
                    },
                )
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    with patch.object(retriever, "_parent_score_map", side_effect=[{"p1": 0.9}, {}]):
        docs = retriever.invoke("FRTB desk requirements")

    meta = docs[0].metadata or {}
    assert meta["expand_parent_route"] == "default"
    assert meta["expand_parent_applied"] is True
    assert meta["expand_parent_reason"] == "default_signal"
    assert meta["expanded_text"]
    assert "parent_expand" in (meta.get("indexing_sources") or [])


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_hyde_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.load_summary_corpus", return_value=[])
@patch("riskagent_agenticrag.rag.advanced_index_retriever.parent_corpus_by_id")
def test_compare_route_expands_multiple_top_docs(mock_parent_by_id, _mock_summary, _mock_hyde):
    from riskagent_agenticrag.rag.advanced_index_retriever import AdvancedIndexConfig, AdvancedIndexRetriever

    mock_parent_by_id.return_value = {
        "p1": Document(page_content="compare parent one " * 120, metadata={"parent_id": "p1", "parent_type": "section"}),
        "p2": Document(page_content="compare parent two " * 120, metadata={"parent_id": "p2", "parent_type": "section"}),
    }
    base = MagicMock(
        invoke=MagicMock(
            return_value=[
                Document(
                    page_content="first compare chunk " * 20,
                    metadata={
                        "parent_id": "p1",
                        "chunk_id": "c1",
                        "source": "a.md",
                        "query_route": "compare",
                        "coarse_score": 0.9,
                        "confidence_gap_to_top1": 0.0,
                    },
                ),
                Document(
                    page_content="second compare chunk " * 20,
                    metadata={
                        "parent_id": "p2",
                        "chunk_id": "c2",
                        "source": "b.md",
                        "query_route": "compare",
                        "coarse_score": 0.8,
                        "confidence_gap_to_top1": 0.25,
                    },
                ),
            ]
        )
    )
    retriever = AdvancedIndexRetriever(
        base_retriever=base,
        persist_dir="/tmp/unused",
        config=AdvancedIndexConfig(expand_parent=True, final_k=4),
    )

    docs = retriever.invoke("Compare FRTB and Basel II.5")

    assert len(docs) == 2
    for doc in docs:
        meta = doc.metadata or {}
        assert meta["expand_parent_route"] == "compare"
        assert meta["expand_parent_applied"] is True
        assert meta["expand_parent_reason"] == "near_top"
        assert meta["expanded_text"]
