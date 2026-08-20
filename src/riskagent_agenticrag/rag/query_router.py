"""TARG (Training-free Adaptive Retrieval Gate) 查询路由.

基于规则的免训练查询复杂性评估: 简单查询跳过检索直接回答, 复杂查询才触发完整检索链路.
核心思想是避免对简单查询执行过重的 rewrite -> retrieve -> critique 链路.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# 金融术语词表 (词边界匹配, 避免短缩写误匹配长单词, 如 "es" 误中 "because")
# XVA 家族补全: fva/mva/colva 曾缺失导致三题被误判 simple 跳过检索 (eval v10b)
_FINANCIAL_TERM_RE = re.compile(
    r"\b(frtb|cva|dva|xva|kva|fva|mva|colva|delta|gamma|vega|volga|vanna|charm|"
    r"var|es|margin|default|exposure|collateral|shortfall|isda|bcbs|basel)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QueryComplexity:
    """查询复杂性评估结果."""

    level: str  # "simple" / "moderate" / "complex"
    needs_retrieval: bool
    needs_rewrite: bool
    needs_fanout: bool
    confidence: float  # 0.0-1.0
    reason: str


def assess_query_complexity(*, question: str) -> QueryComplexity:
    """评估查询复杂性, 决定是否需要检索.

    规则:
    - simple: 长度<15字符, 无问号嵌套, 无比较词, 无多跳信号 -> 跳过检索
    - moderate: 标准查询, 需要检索但不需要 fanout
    - complex: 包含 compare/numeric/multi-hop 信号, 需要完整链路 + fanout
    """
    q = str(question or "").strip()
    q_lower = q.lower()

    # 复杂性信号
    has_compare = any(x in q_lower for x in ("compare", "difference", "vs", "versus", "between", "distinguish"))
    has_numeric = any(x in q_lower for x in ("calculate", "value", "limit", "threshold", "how much", "how many", "number"))
    has_multihop = q.count("?") > 1 or any(x in q_lower for x in ("because", "therefore", "then", "chain"))
    has_financial_term = bool(_FINANCIAL_TERM_RE.search(q))

    length = len(q)

    # 简单查询: 短 + 无复杂信号 + 无金融术语.
    # 金融术语查询即使很短也必须检索 grounding (合规场景定义类问题需要引用原文,
    # 曾因未检查 has_financial_term 导致 "What is XVA?" 等 9 题跳过检索直接裸答).
    if length < 15 and not (has_compare or has_numeric or has_multihop or has_financial_term):
        return QueryComplexity(
            level="simple", needs_retrieval=False, needs_rewrite=False,
            needs_fanout=False, confidence=0.8, reason="short_query_no_complexity_signal"
        )

    # 复杂查询: 有比较/数值/多跳信号
    if has_compare or has_numeric or has_multihop:
        return QueryComplexity(
            level="complex", needs_retrieval=True, needs_rewrite=True,
            needs_fanout=True, confidence=0.75, reason=f"complex_signal_{has_compare}_{has_numeric}_{has_multihop}"
        )

    # 中等查询: 默认
    return QueryComplexity(
        level="moderate", needs_retrieval=True, needs_rewrite=True,
        needs_fanout=False, confidence=0.6, reason="default_moderate"
    )
