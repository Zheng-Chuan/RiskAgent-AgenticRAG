"""Agentic RAG 检索工具封装层单元测试 (RFC-004 阶段一)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document


def _build_mock_retriever() -> MagicMock:
    """构建模拟的 AdvancedIndexRetriever, 包含完整链路结构.

    链路: AdvancedIndexRetriever._base (QueryIntelligentRetriever) ._base (HybridRetriever)
    HybridRetriever 内部有 _dense, _sparse_docs, _bm25, _parent_by_id
    """
    dense = MagicMock()
    doc = Document(
        page_content="FRTB delta risk capital charge",
        metadata={
            "chunk_id": "c1",
            "source": "frtb.pdf",
            "section_path": "delta/risk",
            "parent_id": "p1",
            "context_brief": "FRTB overview",
            "dense_score": 0.85,
        },
    )
    dense.invoke = MagicMock(return_value=[doc])

    sparse_docs = [
        Document(
            page_content="FRTB delta risk content",
            metadata={
                "chunk_id": "c1",
                "source": "frtb.pdf",
                "section_path": "delta/risk",
                "parent_id": "p1",
                "context_brief": "FRTB overview",
            },
        ),
        Document(
            page_content="CVA credit valuation adjustment",
            metadata={
                "chunk_id": "c2",
                "source": "cva.pdf",
                "section_path": "cva/intro",
                "parent_id": "p2",
            },
        ),
    ]

    bm25 = MagicMock()
    bm25.get_scores = MagicMock(return_value=[1.5, 0.3])

    parent = Document(page_content="parent document full text", metadata={"chunk_id": "p1"})
    parent_by_id = {"p1": parent}

    hybrid = MagicMock()
    hybrid._dense = dense
    hybrid._sparse_docs = sparse_docs
    hybrid._bm25 = bm25

    query_intel = MagicMock()
    query_intel._base = hybrid

    retriever = MagicMock()
    retriever._base = query_intel
    retriever._parent_by_id = parent_by_id

    return retriever


# ===========================================================================
# context 管理
# ===========================================================================

@pytest.mark.unit
def test_set_and_get_retriever_context():
    """set_retriever_context 后 _get_retriever 应返回设置的 retriever."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        _get_retriever,
        set_retriever_context,
    )

    mock_retriever = MagicMock()
    set_retriever_context(mock_retriever)
    assert _get_retriever() is mock_retriever


@pytest.mark.unit
def test_get_retriever_raises_without_context():
    """未设置 context 时 _get_retriever 应抛 RuntimeError."""
    from unittest.mock import patch
    from riskagent_agenticrag.agents.retrieval_tools import _get_retriever

    # mock contextvar get 抛 LookupError, 模拟 contextvar 从未设置的情况
    with patch("riskagent_agenticrag.agents.retrieval_tools._retriever_ctx") as mock_ctx:
        mock_ctx.get.side_effect = LookupError("no value set")
        with pytest.raises(RuntimeError, match="Retriever context not set"):
            _get_retriever()


# ===========================================================================
# _doc_to_dict
# ===========================================================================

@pytest.mark.unit
def test_doc_to_dict_includes_core_fields():
    """_doc_to_dict 应包含 chunk_id, text, source."""
    from riskagent_agenticrag.agents.retrieval_tools import _doc_to_dict

    doc = Document(
        page_content="content text",
        metadata={"chunk_id": "c1", "source": "src.pdf", "section_path": "sec/a"},
    )
    result = _doc_to_dict(doc, score=0.9)
    assert result["chunk_id"] == "c1"
    assert result["text"] == "content text"
    assert result["source"] == "src.pdf"
    assert result["score"] == 0.9
    assert result["section_path"] == "sec/a"


@pytest.mark.unit
def test_doc_to_dict_without_score():
    """无 score 参数时结果不应包含 score 字段."""
    from riskagent_agenticrag.agents.retrieval_tools import _doc_to_dict

    doc = Document(page_content="text", metadata={"chunk_id": "c1"})
    result = _doc_to_dict(doc)
    assert "score" not in result


# ===========================================================================
# _extract 辅助函数
# ===========================================================================

@pytest.mark.unit
def test_extract_hybrid_retriever():
    """_extract_hybrid_retriever 应从 retriever 链路提取 HybridRetriever."""
    from riskagent_agenticrag.agents.retrieval_tools import _extract_hybrid_retriever

    retriever = _build_mock_retriever()
    hybrid = _extract_hybrid_retriever(retriever)
    assert hybrid is not None


@pytest.mark.unit
def test_extract_hybrid_retriever_returns_none_on_attribute_error():
    """retriever 无 _base._base 时应返回 None."""
    from riskagent_agenticrag.agents.retrieval_tools import _extract_hybrid_retriever

    retriever = MagicMock()
    retriever._base = None
    assert _extract_hybrid_retriever(retriever) is None


@pytest.mark.unit
def test_extract_sparse_docs():
    """_extract_sparse_docs 应返回 sparse_docs 列表."""
    from riskagent_agenticrag.agents.retrieval_tools import _extract_sparse_docs

    retriever = _build_mock_retriever()
    docs = _extract_sparse_docs(retriever)
    assert len(docs) == 2


@pytest.mark.unit
def test_extract_sparse_docs_empty_when_no_hybrid():
    """无 hybrid 时应返回空列表."""
    from riskagent_agenticrag.agents.retrieval_tools import _extract_sparse_docs

    retriever = MagicMock()
    retriever._base = None
    assert _extract_sparse_docs(retriever) == []


# ===========================================================================
# semantic_search 工具
# ===========================================================================

@pytest.mark.unit
def test_semantic_search_returns_docs():
    """semantic_search 应返回检索到的文档列表."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        semantic_search,
        set_retriever_context,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = semantic_search.invoke({"query": "FRTB", "top_k": 5})
    assert len(result) == 1
    assert result[0]["chunk_id"] == "c1"
    assert result[0]["score"] == 0.85


@pytest.mark.unit
def test_semantic_search_returns_empty_when_no_dense():
    """无 dense retriever 时应返回空列表."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        semantic_search,
        set_retriever_context,
    )

    retriever = MagicMock()
    retriever._base = None
    set_retriever_context(retriever)

    result = semantic_search.invoke({"query": "FRTB", "top_k": 5})
    assert result == []


# ===========================================================================
# structured_lookup 工具
# ===========================================================================

@pytest.mark.unit
def test_structured_lookup_by_source():
    """structured_lookup 应按 source 子串匹配文档."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        set_retriever_context,
        structured_lookup,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = structured_lookup.invoke({"source": "frtb", "section_path": ""})
    assert len(result) == 1
    assert result[0]["source"] == "frtb.pdf"


@pytest.mark.unit
def test_structured_lookup_empty_params_returns_empty():
    """source 和 section_path 都为空时应返回空列表."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        set_retriever_context,
        structured_lookup,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = structured_lookup.invoke({"source": "", "section_path": ""})
    assert result == []


# ===========================================================================
# chunk_read 工具
# ===========================================================================

@pytest.mark.unit
def test_chunk_read_returns_full_content():
    """chunk_read 应返回 chunk 的完整内容和上下文."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        chunk_read,
        set_retriever_context,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = chunk_read.invoke({"chunk_id": "c1"})
    assert result["chunk_id"] == "c1"
    assert "FRTB delta risk content" in result["text"]
    assert result["source"] == "frtb.pdf"
    assert result["parent_id"] == "p1"
    assert "parent_text" in result
    assert isinstance(result["neighbors"], list)


@pytest.mark.unit
def test_chunk_read_empty_chunk_id_returns_empty():
    """空 chunk_id 应返回空字典."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        chunk_read,
        set_retriever_context,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = chunk_read.invoke({"chunk_id": ""})
    assert result == {}


@pytest.mark.unit
def test_chunk_read_not_found_returns_empty():
    """找不到的 chunk_id 应返回空字典."""
    from riskagent_agenticrag.agents.retrieval_tools import (
        chunk_read,
        set_retriever_context,
    )

    retriever = _build_mock_retriever()
    set_retriever_context(retriever)

    result = chunk_read.invoke({"chunk_id": "nonexistent"})
    assert result == {}
