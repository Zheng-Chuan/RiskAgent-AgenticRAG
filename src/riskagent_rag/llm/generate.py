"""LLM 输出生成.

这个模块提供一个极简的 LLM adapter.

目标.
- MVP 阶段优先保证可运行, 可演示.
- 如果用户配置了 API key, 则走真实模型生成.
- 如果没有配置 API key, 则返回 deterministic 文本, 仍然携带检索到的上下文片段, 便于验证 RAG 链路.

环境变量.
- OPENAI_API_KEY 或 LLM_API_KEY: 启用模型生成.
- LLM_BASE_URL: 可选, OpenAI compatible base url.
- LLM_MODEL: 可选, 默认 gpt-4o-mini.
"""

from __future__ import annotations

import os
from typing import Iterable

from langchain_core.documents import Document


def _format_context(docs: Iterable[Document], limit: int = 1200) -> str:
    # 将检索到的 Document 列表格式化成上下文文本.
    # 这里用 limit 做一个粗粒度截断, 避免 prompt 太长.
    parts: list[str] = []
    total = 0
    for i, d in enumerate(docs, start=1):
        text = (d.page_content or "").strip()
        if not text:
            continue
        chunk = f"[ctx {i}]\n{text}\n"
        total += len(chunk)
        if total > limit:
            break
        parts.append(chunk)
    return "\n".join(parts).strip()


def generate_answer(question: str, docs: list[Document]) -> str:
    # 统一入口, 输入 question + docs, 输出 answer 字符串.
    # 注意: citations 的结构化输出在 pipeline.extract_citations 里实现.

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if api_key:
        # 有 key 时, 使用 langchain_openai 的 ChatOpenAI.
        # base_url 支持 OpenAI compatible API, 便于后续接入不同大模型服务.
        from langchain_openai import ChatOpenAI

        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        base_url = os.getenv("LLM_BASE_URL")

        llm = ChatOpenAI(model=model, base_url=base_url or None, api_key=api_key)

        context = _format_context(docs)
        prompt = (
            "You are a helpful assistant explaining financial derivatives and risk concepts to software engineers. "
            "Answer using only the provided context. If context is insufficient, say you do not know.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n"
        )
        # 这里直接用字符串 prompt 做 invoke, MVP 先不引入复杂的 prompt template.
        msg = llm.invoke(prompt)
        return getattr(msg, "content", str(msg))

    # 没有 key 时, 走 fallback.
    # 这个模式的目的不是回答质量, 而是让用户看到检索的内容, 并确认数据链路正确.
    context = _format_context(docs, limit=1600)
    if not context:
        return (
            "I do not have enough context in docs/sources to answer this question yet. "
            "Add more documents and rebuild the index."
        )

    return (
        "MVP mode: no API key found, using deterministic answer.\n\n"
        f"Question: {question}\n\n"
        "Relevant excerpts:\n"
        f"{context}\n\n"
        "Next: set OPENAI_API_KEY (or LLM_API_KEY) to enable model generated answers."
    )
