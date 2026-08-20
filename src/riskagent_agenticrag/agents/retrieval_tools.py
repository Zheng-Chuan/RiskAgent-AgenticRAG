"""Agentic RAG 检索工具封装层 (RFC-004 阶段一).

把现有检索能力封装为 4 个 LLM 可调用的工具:
- semantic_search: 语义检索 (dense), 适合概念性查询
- keyword_search: 关键词检索 (BM25), 适合术语/编号/精确匹配
- structured_lookup: 按 source/section 精确定位文档块
- chunk_read: 读取指定 chunk_id 的完整内容和上下文

设计要点:
- 工具是模块级 @tool 实例, 可直接 import
- 工具执行时通过 contextvars 获取当前 retriever, runner 在调用前设置 context
- 复用现有 retriever 内部组件 (dense / sparse / parent), 不重建索引
"""
from __future__ import annotations

import contextvars
from typing import Any

from langchain_core.documents import Document
from langchain_core.tools import tool

from riskagent_agenticrag.rag.utils import tokenize

# contextvar: 保存当前 retriever, 工具执行时从中获取内部组件
_retriever_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("agentic_rag_retriever")


def set_retriever_context(retriever: Any) -> None:
    """设置当前 retriever context, 供工具函数使用.

    runner 在执行 agent loop 前调用此函数, 把构建好的 retriever 注入 context.
    """
    _retriever_ctx.set(retriever)


def _get_retriever() -> Any:
    """获取当前 context 中的 retriever.

    Raises:
        RuntimeError: 未设置 retriever context 时抛出.
    """
    try:
        return _retriever_ctx.get()
    except LookupError as exc:
        raise RuntimeError("Retriever context not set. Call set_retriever_context first.") from exc


# ---------------------------------------------------------------------------
# 内部 helper: 从顶层 retriever 提取所需组件
# ---------------------------------------------------------------------------

def _extract_hybrid_retriever(retriever: Any) -> Any:
    """从 AdvancedIndexRetriever 中提取 HybridRetriever.

    链路: AdvancedIndexRetriever._base (QueryIntelligentRetriever) ._base (HybridRetriever)
    """
    try:
        return retriever._base._base
    except AttributeError:
        return None


def _extract_dense_retriever(retriever: Any) -> Any:
    """从顶层 retriever 中提取 DenseMilvusRetriever."""
    hybrid = _extract_hybrid_retriever(retriever)
    if hybrid is None:
        return None
    return getattr(hybrid, "_dense", None)


def _extract_sparse_docs(retriever: Any) -> list[Document]:
    """从顶层 retriever 中提取 sparse docs (全量 chunk 语料)."""
    hybrid = _extract_hybrid_retriever(retriever)
    if hybrid is None:
        return []
    return list(getattr(hybrid, "_sparse_docs", []) or [])


def _extract_bm25(retriever: Any) -> Any:
    """从顶层 retriever 中提取 BM25Okapi 实例."""
    hybrid = _extract_hybrid_retriever(retriever)
    if hybrid is None:
        return None
    return getattr(hybrid, "_bm25", None)


def _extract_parent_by_id(retriever: Any) -> dict[str, Document]:
    """从顶层 retriever 中提取 parent_id -> parent Document 映射."""
    return dict(getattr(retriever, "_parent_by_id", {}) or {})


def _doc_to_dict(d: Document, score: float | None = None) -> dict[str, Any]:
    """将 Document 转为可序列化的 dict, 供 LLM 工具结果使用."""
    meta = d.metadata or {}
    out: dict[str, Any] = {
        "chunk_id": str(meta.get("chunk_id", "")),
        "text": str(d.page_content or ""),
        "source": str(meta.get("source", "")),
    }
    if score is not None:
        out["score"] = float(score)
    if meta.get("section_path"):
        out["section_path"] = str(meta.get("section_path"))
    if meta.get("parent_id"):
        out["parent_id"] = str(meta.get("parent_id"))
    if meta.get("context_brief"):
        out["context_brief"] = str(meta.get("context_brief"))
    return out


# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------

@tool
def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """基于语义相似度检索文档, 适合概念性查询.

    Args:
        query: 查询文本
        top_k: 返回数量

    Returns:
        文档列表, 每个包含 chunk_id, text, source, score
    """
    retriever = _get_retriever()
    dense = _extract_dense_retriever(retriever)
    if dense is None:
        return []
    docs = list(dense.invoke(query))
    k = max(1, int(top_k))
    out: list[dict] = []
    for d in docs[:k]:
        meta = d.metadata or {}
        score = float(meta.get("dense_score", 0.0))
        out.append(_doc_to_dict(d, score=score))
    return out


@tool
def keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """基于关键词检索文档, 适合术语/编号/精确匹配.

    Args:
        query: 查询文本
        top_k: 返回数量

    Returns:
        文档列表
    """
    retriever = _get_retriever()
    bm25 = _extract_bm25(retriever)
    sparse_docs = _extract_sparse_docs(retriever)
    if bm25 is None or not sparse_docs:
        return []
    # 复用项目统一的 tokenize, 保证和建索时分词一致
    toks = tokenize(query)
    if not toks:
        return []
    scores = bm25.get_scores(toks)
    k = max(1, int(top_k))
    top_idx = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[:k]
    # 归一化分数, 方便 LLM 判断相关性
    max_s = float(max((float(scores[i]) for i in top_idx), default=0.0))
    denom = max_s if max_s > 0 else 1.0
    out: list[dict] = []
    for i in top_idx:
        if i >= len(sparse_docs):
            continue
        d = sparse_docs[i]
        score = float(scores[i]) / denom
        out.append(_doc_to_dict(d, score=score))
    return out


@tool
def structured_lookup(source: str = "", section_path: str = "") -> list[dict]:
    """按 source/section 精确定位文档块.

    Args:
        source: 文件名或路径 (子串匹配, 不区分大小写)
        section_path: 章节路径 (子串匹配, 不区分大小写)

    Returns:
        匹配的文档块列表
    """
    retriever = _get_retriever()
    sparse_docs = _extract_sparse_docs(retriever)
    if not sparse_docs:
        return []
    src_q = str(source or "").strip().lower()
    sec_q = str(section_path or "").strip().lower()
    # 两个参数都为空时不返回, 避免全量扫描
    if not src_q and not sec_q:
        return []
    out: list[dict] = []
    for d in sparse_docs:
        meta = d.metadata or {}
        d_source = str(meta.get("source", "")).lower()
        d_section = str(meta.get("section_path", "")).lower()
        match = True
        if src_q and src_q not in d_source:
            match = False
        if sec_q and sec_q not in d_section:
            match = False
        if match:
            out.append(_doc_to_dict(d))
        # 限制返回数量, 避免上下文膨胀
        if len(out) >= 20:
            break
    return out


@tool
def chunk_read(chunk_id: str) -> dict:
    """读取指定 chunk_id 的完整内容和上下文.

    Args:
        chunk_id: 文档块 ID

    Returns:
        包含 text, context_brief, parent_id, neighbors 的字典;
        找不到时返回空字典.
    """
    retriever = _get_retriever()
    sparse_docs = _extract_sparse_docs(retriever)
    parent_by_id = _extract_parent_by_id(retriever)
    cid = str(chunk_id or "").strip()
    if not cid:
        return {}

    # 查找目标 chunk
    target: Document | None = None
    for d in sparse_docs:
        if str((d.metadata or {}).get("chunk_id", "")).strip() == cid:
            target = d
            break
    if target is None:
        return {}

    meta = target.metadata or {}
    parent_id = str(meta.get("parent_id", "")).strip()

    # 获取 parent 文档
    parent_doc = parent_by_id.get(parent_id) if parent_id else None

    # 获取 siblings (同 parent_id 的其他 chunks), 用于上下文补全
    neighbors: list[dict] = []
    if parent_id:
        for d in sparse_docs:
            d_meta = d.metadata or {}
            if str(d_meta.get("parent_id", "")).strip() == parent_id:
                d_cid = str(d_meta.get("chunk_id", "")).strip()
                if d_cid and d_cid != cid:
                    neighbors.append({
                        "chunk_id": d_cid,
                        "text": str(d.page_content or "")[:200],
                        "source": str(d_meta.get("source", "")),
                    })
                    if len(neighbors) >= 5:
                        break

    out: dict[str, Any] = {
        "chunk_id": cid,
        "text": str(target.page_content or ""),
        "source": str(meta.get("source", "")),
        "section_path": str(meta.get("section_path", "")),
        "context_brief": str(meta.get("context_brief", "")),
        "parent_id": parent_id,
        "neighbors": neighbors,
    }
    if parent_doc is not None:
        out["parent_text"] = str(parent_doc.page_content or "")[:1000]
    return out
