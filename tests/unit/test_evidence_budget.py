"""SEAL-RAG 证据预算管理器单元测试 (RFC-001 FR-12)."""

from __future__ import annotations

import pytest
from langchain_core.documents import Document


def _make_doc(text: str, chunk_id: str = "c1") -> Document:
    """创建测试用 Document."""
    return Document(page_content=text, metadata={"chunk_id": chunk_id})


# ===========================================================================
# add: 容量未满时直接加入
# ===========================================================================

@pytest.mark.unit
def test_add_below_capacity_returns_false():
    """容量未满时 add 应返回 False (未替换)."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    result = budget.add(_make_doc("doc1"), score=0.8, round=1, source="dense")
    assert result is False
    assert len(budget.get_docs()) == 1


@pytest.mark.unit
def test_add_at_capacity_replaces_weakest():
    """容量已满时 add 应替换最弱的证据, 返回 True."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=3)
    budget.add(_make_doc("doc1", "c1"), score=0.5, round=1, source="dense")
    budget.add(_make_doc("doc2", "c2"), score=0.8, round=1, source="dense")
    budget.add(_make_doc("doc3", "c3"), score=0.3, round=1, source="sparse")

    # 新证据分数 0.6 > 最弱 0.3, 应替换
    replaced = budget.add(_make_doc("doc4", "c4"), score=0.6, round=2, source="rerank")
    assert replaced is True
    docs = budget.get_docs()
    assert len(docs) == 3
    # 最弱的 0.3 (doc3) 应被替换
    chunk_ids = [d.metadata["chunk_id"] for d in docs]
    assert "c3" not in chunk_ids
    assert "c4" in chunk_ids


@pytest.mark.unit
def test_add_at_capacity_drops_weaker():
    """容量已满且新证据弱于最弱时应丢弃, 返回 False."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=2)
    budget.add(_make_doc("doc1", "c1"), score=0.8, round=1, source="dense")
    budget.add(_make_doc("doc2", "c2"), score=0.7, round=1, source="sparse")

    # 新证据分数 0.1 < 最弱 0.7, 应丢弃
    replaced = budget.add(_make_doc("doc3", "c3"), score=0.1, round=2, source="rerank")
    assert replaced is False
    assert len(budget.get_docs()) == 2


# ===========================================================================
# merge: 批量合并
# ===========================================================================

@pytest.mark.unit
def test_merge_returns_replacement_count():
    """merge 应返回替换次数."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=3)
    budget.add(_make_doc("doc1", "c1"), score=0.5, round=1, source="dense")
    budget.add(_make_doc("doc2", "c2"), score=0.3, round=1, source="sparse")
    budget.add(_make_doc("doc3", "c3"), score=0.4, round=1, source="dense")

    # 新批次: 0.9 替换 0.3, 0.2 被丢弃
    new_docs = [_make_doc("doc4", "c4"), _make_doc("doc5", "c5")]
    new_scores = [0.9, 0.2]
    replaced = budget.merge(new_docs, new_scores, round=2, source="rerank")
    assert replaced == 1  # 只有 0.9 替换了 0.3


# ===========================================================================
# get_docs / get_scores: 按分数降序
# ===========================================================================

@pytest.mark.unit
def test_get_docs_and_scores_sorted_desc():
    """get_docs 和 get_scores 应按分数降序返回."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    budget.add(_make_doc("low", "c1"), score=0.2, round=1, source="dense")
    budget.add(_make_doc("high", "c2"), score=0.9, round=1, source="dense")
    budget.add(_make_doc("mid", "c3"), score=0.5, round=1, source="sparse")

    scores = budget.get_scores()
    assert scores == [0.9, 0.5, 0.2]

    docs = budget.get_docs()
    assert docs[0].metadata["chunk_id"] == "c2"
    assert docs[1].metadata["chunk_id"] == "c3"
    assert docs[2].metadata["chunk_id"] == "c1"


# ===========================================================================
# stats: 统计信息
# ===========================================================================

@pytest.mark.unit
def test_stats_empty_budget():
    """空 budget 的 stats 应返回合理默认值."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    stats = budget.stats()
    assert stats["capacity"] == 5
    assert stats["current_size"] == 0
    assert stats["top_score"] == 0.0
    assert stats["min_score"] == 0.0
    assert stats["avg_score"] == 0.0
    assert stats["sources"] == []
    assert stats["rounds"] == []


@pytest.mark.unit
def test_stats_with_entries():
    """有证据时 stats 应正确反映当前状态."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    budget.add(_make_doc("doc1", "c1"), score=0.8, round=1, source="dense")
    budget.add(_make_doc("doc2", "c2"), score=0.6, round=2, source="sparse")

    stats = budget.stats()
    assert stats["capacity"] == 5
    assert stats["current_size"] == 2
    assert stats["top_score"] == 0.8
    assert stats["min_score"] == 0.6
    assert abs(stats["avg_score"] - 0.7) < 0.01
    assert set(stats["sources"]) == {"dense", "sparse"}
    assert set(stats["rounds"]) == {1, 2}


# ===========================================================================
# dedup: 同一 chunk 跨轮重复出现只占一个槽位
# ===========================================================================

@pytest.mark.unit
def test_add_duplicate_chunk_does_not_occupy_new_slot():
    """同一 chunk_id 重复 add 不应占新槽位 (v10e recall 回归根因修复)."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    budget.add(_make_doc("doc1", "c1"), score=0.8, round=1, source="dense")
    # 第二轮检索又检回同一 chunk, 分数更低
    budget.add(_make_doc("doc1", "c1"), score=0.5, round=2, source="rerank")
    assert len(budget.get_docs()) == 1
    # 分数保留较高的那个
    assert budget.get_scores() == [0.8]

@pytest.mark.unit
def test_add_duplicate_chunk_updates_score_to_max():
    """同一 chunk 以更高分数再次出现时应更新分数, 仍只占一个槽位."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    budget.add(_make_doc("doc1", "c1"), score=0.5, round=1, source="dense")
    budget.add(_make_doc("doc1", "c1"), score=0.9, round=2, source="rerank")
    assert len(budget.get_docs()) == 1
    assert budget.get_scores() == [0.9]

@pytest.mark.unit
def test_merge_duplicate_frees_slot_for_gold():
    """重复 chunk 不再挤占槽位, 其他证据能进入 budget.

    场景还原 v10e q14: 第一轮 5 个 chunk, 第二轮检索回其中 2 个重复项.
    修复前: 重复项占 2 个槽位, 挤掉 gold; 修复后: gold 保留.
    """
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=3)
    # 第一轮: 3 个 chunk 装满
    budget.merge(
        [_make_doc("a", "c1"), _make_doc("b", "c2"), _make_doc("gold", "c3")],
        [0.9, 0.8, 0.3], round=1, source="dense",
    )
    # 第二轮: c1 c2 重复出现 (分数更高), 另有新 chunk c4
    replaced = budget.merge(
        [_make_doc("a", "c1"), _make_doc("b", "c2"), _make_doc("new", "c4")],
        [0.95, 0.85, 0.4], round=2, source="rerank",
    )
    docs = budget.get_docs()
    chunk_ids = [d.metadata["chunk_id"] for d in docs]
    # 重复项只占一个槽位, c4 得以进入, gold (c3) 被更强的新证据替换属正常竞争
    assert chunk_ids.count("c1") == 1
    assert chunk_ids.count("c2") == 1
    assert len(chunk_ids) == len(set(chunk_ids))  # 无重复
    assert replaced == 1  # 只有 c4 替换了 gold, 两个重复项不再挤占

@pytest.mark.unit
def test_add_doc_without_chunk_id_dedup_by_content():
    """无 chunk_id 的 doc 按内容去重."""
    from riskagent_agenticrag.rag.evidence_budget import EvidenceBudget

    budget = EvidenceBudget(capacity=5)
    budget.add(Document(page_content="same content"), score=0.5, round=1, source="dense")
    budget.add(Document(page_content="same content"), score=0.7, round=2, source="rerank")
    assert len(budget.get_docs()) == 1
    assert budget.get_scores() == [0.7]
