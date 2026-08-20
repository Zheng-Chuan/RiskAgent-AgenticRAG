"""CRAG 降级策略单元测试 (FR-10)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest


# ===========================================================================
# _bump_config_k
# ===========================================================================

@dataclass(frozen=True)
class _FakeConfig:
    """模拟 retriever config, 包含 k 相关字段."""
    k: int = 8
    dense_k: int = 10
    final_k: int = 4
    other_field: str = "value"


@pytest.mark.unit
def test_bump_config_k_replaces_all_k_fields():
    """_bump_config_k 应替换 config 中所有 k 相关字段."""
    from riskagent_agenticrag.rag.crag_strategies import _bump_config_k

    config = _FakeConfig(k=8, dense_k=10, final_k=4, other_field="value")
    new_config = _bump_config_k(config, 20)

    assert new_config.k == 20
    assert new_config.dense_k == 20
    assert new_config.final_k == 20
    # 非 k 字段保持不变
    assert new_config.other_field == "value"


@pytest.mark.unit
def test_bump_config_k_none_returns_none():
    """_bump_config_k 对 None 输入应原样返回."""
    from riskagent_agenticrag.rag.crag_strategies import _bump_config_k

    assert _bump_config_k(None, 20) is None


@pytest.mark.unit
def test_bump_config_k_no_k_fields_returns_original():
    """config 无 k 字段时应原样返回."""
    from riskagent_agenticrag.rag.crag_strategies import _bump_config_k

    @dataclass(frozen=True)
    class _NoKConfig:
        name: str = "test"

    config = _NoKConfig(name="test")
    result = _bump_config_k(config, 20)
    assert result is config


# ===========================================================================
# _expand_retriever_k
# ===========================================================================

@pytest.mark.unit
def test_expand_retriever_k_none_retriever():
    """_expand_retriever_k 对 None retriever 应安全返回."""
    from riskagent_agenticrag.rag.crag_strategies import _expand_retriever_k

    _expand_retriever_k(None, 20)  # 不应抛异常


@pytest.mark.unit
def test_expand_retriever_k_updates_config_recursively():
    """_expand_retriever_k 应递归更新 retriever 链路的 _config."""
    from riskagent_agenticrag.rag.crag_strategies import _expand_retriever_k

    inner = MagicMock()
    inner._config = _FakeConfig(k=4)
    inner._base = None
    inner._dense = None

    outer = MagicMock()
    outer._config = _FakeConfig(k=8)
    outer._base = inner
    outer._dense = None

    _expand_retriever_k(outer, 20)

    assert outer._config.k == 20
    assert inner._config.k == 20


# ===========================================================================
# expand_retrieval
# ===========================================================================

@pytest.mark.unit
def test_expand_retrieval_returns_docs():
    """expand_retrieval 应返回检索到的文档列表."""
    from riskagent_agenticrag.rag.crag_strategies import expand_retrieval
    from langchain_core.documents import Document

    doc = Document(page_content="FRTB content", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[doc]))

    result = expand_retrieval(retriever=retriever, query="FRTB", current_k=4, max_k=10)
    assert len(result) == 1
    assert result[0].metadata["chunk_id"] == "c1"


@pytest.mark.unit
def test_expand_retrieval_caps_at_max_k():
    """expand_retrieval 返回的文档不应超过 max_k."""
    from riskagent_agenticrag.rag.crag_strategies import expand_retrieval
    from langchain_core.documents import Document

    docs = [Document(page_content=f"doc {i}", metadata={"chunk_id": f"c{i}"}) for i in range(15)]
    retriever = MagicMock(invoke=MagicMock(return_value=docs))
    # 避免 MagicMock 自动创建 _base/_dense 导致 _expand_retriever_k 无限递归
    retriever._base = None
    retriever._dense = None

    # current_k=4, 翻倍后 expanded_k = min(8, 10) = 8
    result = expand_retrieval(retriever=retriever, query="test", current_k=4, max_k=10)
    assert len(result) <= 8


@pytest.mark.unit
def test_expand_retrieval_falls_back_on_error():
    """expand_retrieval 在调整失败时应回退为原样 invoke."""
    from riskagent_agenticrag.rag.crag_strategies import expand_retrieval
    from langchain_core.documents import Document

    doc = Document(page_content="fallback content", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[doc]))
    # retriever._config 赋值时抛异常, 触发回退
    type(retriever)._config = property(lambda self: (_ for _ in ()).throw(RuntimeError("no config")))

    result = expand_retrieval(retriever=retriever, query="test", current_k=4, max_k=10)
    assert len(result) == 1


# ===========================================================================
# rewrite_and_retrieve
# ===========================================================================

@pytest.mark.unit
@patch("riskagent_agenticrag.rag.agentic_primitives.revise_query", return_value="revised query")
def test_rewrite_and_retrieve_returns_new_query_and_docs(mock_revise):
    """rewrite_and_retrieve 应返回 (new_query, docs)."""
    from riskagent_agenticrag.rag.crag_strategies import rewrite_and_retrieve
    from langchain_core.documents import Document

    doc = Document(page_content="content", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[doc]))

    new_query, docs = rewrite_and_retrieve(
        retriever=retriever, question="what is frtb", previous_query="frtb", docs_count=0
    )
    assert new_query == "revised query"
    assert len(docs) == 1


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.agentic_primitives.revise_query", side_effect=RuntimeError("LLM failed"))
def test_rewrite_and_retrieve_falls_back_on_error(mock_revise):
    """rewrite_and_retrieve 在改写失败时应回退到原 query 检索."""
    from riskagent_agenticrag.rag.crag_strategies import rewrite_and_retrieve
    from langchain_core.documents import Document

    doc = Document(page_content="fallback", metadata={"chunk_id": "c1"})
    retriever = MagicMock(invoke=MagicMock(return_value=[doc]))

    new_query, docs = rewrite_and_retrieve(
        retriever=retriever, question="what is frtb", previous_query="frtb original", docs_count=0
    )
    # 回退到 previous_query
    assert new_query == "frtb original"
    assert len(docs) == 1


@pytest.mark.unit
@patch("riskagent_agenticrag.rag.agentic_primitives.revise_query", side_effect=RuntimeError("LLM failed"))
def test_rewrite_and_retrieve_handles_invoke_failure(mock_revise):
    """rewrite_and_retrieve 在检索也失败时应返回空列表."""
    from riskagent_agenticrag.rag.crag_strategies import rewrite_and_retrieve

    retriever = MagicMock(invoke=MagicMock(side_effect=RuntimeError("retriever down")))

    new_query, docs = rewrite_and_retrieve(
        retriever=retriever, question="what is frtb", previous_query="frtb", docs_count=0
    )
    assert new_query == "frtb"
    assert docs == []
