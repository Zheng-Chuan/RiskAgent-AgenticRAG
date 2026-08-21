"""CRAG (Corrective RAG) 降级策略 -- 三档纠错检索的 action 实现 (FR-10).

提供两个降级 action, 对应 CRAG 评估中 insufficient / irrelevant 两档:
- expand_retrieval: irrelevant 档位, 扩大 top_k 放宽过滤重新检索
- rewrite_and_retrieve: insufficient 档位, 重写查询再检索

所有策略均用 try/except 包裹, 失败时回退到普通检索, 保证主流程不中断.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from langchain_core.documents import Document  # noqa: F401  # 保留类型引用便于扩展

# retriever 链路中常见的 k 相关字段名, 用于扩大 top_k 时统一替换
_K_FIELDS = (
    "k",
    "dense_k",
    "sparse_k",
    "rerank_k",
    "final_k",
    "candidate_k",
    "per_query_k",
    "summary_k",
    "hyde_k",
)


def _bump_config_k(config: Any, new_k: int) -> Any:
    """用 dataclasses.replace 把 config 中所有 k 相关字段替换为 new_k.

    config 通常是 frozen dataclass, 不能直接 setattr, 因此用 replace 生成新实例.
    没有 k 字段或替换失败时原样返回 config.
    """
    if config is None:
        return config
    updates: dict[str, int] = {}
    for attr in _K_FIELDS:
        if hasattr(config, attr):
            updates[attr] = int(new_k)
    if not updates:
        return config
    try:
        return replace(config, **updates)
    except Exception:
        return config


def _expand_retriever_k(retriever: Any, new_k: int) -> None:
    """递归调整 retriever 链路的 k 配置, 让后续 invoke 召回更多候选.

    retriever 链路: AdvancedIndexRetriever -> QueryIntelligentRetriever -> HybridRetriever -> DenseMilvusRetriever
    逐层用替换后的 config 重新赋值给 _config, 并递归处理 _base / _dense 子 retriever.
    """
    if retriever is None:
        return
    config = getattr(retriever, "_config", None)
    if config is not None:
        new_config = _bump_config_k(config, new_k)
        if new_config is not config:
            try:
                # retriever 实例本身不是 frozen dataclass, 可直接赋值
                retriever._config = new_config
            except Exception:
                pass  # 赋值失败不影响后续 invoke
    # 递归处理内层 retriever (QueryIntelligentRetriever / HybridRetriever 都用 _base)
    base = getattr(retriever, "_base", None)
    if base is not None:
        _expand_retriever_k(base, new_k)
    # DenseMilvusRetriever 挂在 HybridRetriever._dense 上
    dense = getattr(retriever, "_dense", None)
    if dense is not None:
        _expand_retriever_k(dense, new_k)


def expand_retrieval(*, retriever, query: str, current_k: int, max_k: int = 20) -> list:
    """irrelevant 档位降级: 扩大 top_k 放宽过滤重新检索.

    将 top_k 翻倍 (上限 max_k), 调整 retriever 内部 k 配置后重新检索.
    返回检索到的 Document 列表, 失败时回退为原样 invoke.
    """
    expanded_k = max(1, min(int(current_k) * 2, int(max_k)))
    try:
        # 调整 retriever 链路的 k, 让后续 invoke 召回更多候选
        _expand_retriever_k(retriever, expanded_k)
        docs = list(retriever.invoke(query))
        # 截取前 expanded_k 条, 控制返回规模
        if expanded_k > 0 and len(docs) > expanded_k:
            return docs[:expanded_k]
        return docs
    except Exception:
        # 调整或检索失败, 回退为原样 invoke
        try:
            return list(retriever.invoke(query))
        except Exception:
            return []


def rewrite_and_retrieve(*, retriever, question: str, previous_query: str, docs_count: int) -> tuple[str, list]:
    """insufficient 档位降级: 重写查询再检索.

    调用 agentic_primitives.revise_query 基于上一轮查询改写, 再用新 query 检索.
    返回 (new_query, docs), 失败时回退为使用原 query 检索.
    """
    try:
        from riskagent_agenticrag.rag import agentic_primitives
        new_query = agentic_primitives.revise_query(question, previous_query)
        docs = list(retriever.invoke(new_query))
        return new_query, docs
    except Exception:
        # 回退: 使用原 query 检索
        fallback_query = str(previous_query or question).strip()
        try:
            docs = list(retriever.invoke(fallback_query))
        except Exception:
            docs = []
        return fallback_query, docs
