"""SEAL-RAG 证据预算管理器 -- 固定容量的证据集, 新证据替换最弱的.

核心思想 (RFC-001 FR-12):
- 维护固定 budget 的证据集, 避免 revise loop 中 context 随轮次无限增长
- 发现更好证据时替换最弱的, 而非追加, 从而抑制 context dilution
- 消费方 (synthesize 节点) 仍然只读 state["docs"], 不感知 budget 存在
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document


@dataclass
class EvidenceEntry:
    """证据条目, 带相关性分数."""

    doc: Document
    score: float          # 相关性分数 (越高越好)
    round: int            # 第几轮检索获得
    source: str           # 来源 (dense/sparse/rerank/hybrid/coarse/unknown)


class EvidenceBudget:
    """固定容量的证据集, 新证据替换最弱的.

    SEAL-RAG 核心策略:
    - 容量固定 (默认 5)
    - 新证据进来时, 如果比最弱的强, 替换之
    - 避免 context dilution
    """

    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self._entries: list[EvidenceEntry] = []

    def add(self, doc: Document, score: float, round: int, source: str) -> bool:
        """添加证据, 返回是否替换了旧证据.

        Args:
            doc: 证据文档
            score: 相关性分数 (越高越好)
            round: 第几轮检索获得
            source: 检索来源标记

        Returns:
            True 表示替换了已有最弱证据; False 表示直接新增或被丢弃
        """
        entry = EvidenceEntry(doc=doc, score=score, round=round, source=source)

        # 容量未满, 直接加入并按分数降序排序
        if len(self._entries) < self.capacity:
            self._entries.append(entry)
            self._entries.sort(key=lambda e: e.score, reverse=True)
            return False  # 未满, 直接加

        # 已满, 和最弱的比较: 更强则替换
        weakest = self._entries[-1]
        if score > weakest.score:
            self._entries[-1] = entry
            self._entries.sort(key=lambda e: e.score, reverse=True)
            return True  # 替换了
        return False  # 不够强, 丢弃

    def merge(self, docs: list[Document], scores: list[float], round: int, source: str) -> int:
        """批量合并新证据, 返回替换次数.

        Args:
            docs: 本轮新检索到的文档列表
            scores: 与 docs 一一对应的相关性分数列表
            round: 第几轮检索获得
            source: 检索来源标记

        Returns:
            替换旧证据的次数 (0 表示全部为新增或全部被丢弃)
        """
        replaced = 0
        for doc, score in zip(docs, scores, strict=False):
            if self.add(doc, score, round, source):
                replaced += 1
        return replaced

    def get_docs(self) -> list[Document]:
        """返回当前证据集的 docs (按分数降序)."""
        return [e.doc for e in self._entries]

    def get_scores(self) -> list[float]:
        """返回当前证据集的分数 (按分数降序)."""
        return [e.score for e in self._entries]

    def stats(self) -> dict[str, Any]:
        """返回统计信息, 用于 debug 与 trace 落盘."""
        return {
            "capacity": self.capacity,
            "current_size": len(self._entries),
            "top_score": self._entries[0].score if self._entries else 0.0,
            "min_score": self._entries[-1].score if self._entries else 0.0,
            "avg_score": sum(e.score for e in self._entries) / len(self._entries) if self._entries else 0.0,
            "sources": list(set(e.source for e in self._entries)),
            "rounds": list(set(e.round for e in self._entries)),
        }
