"""LLM 输出生成."""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from langchain_core.documents import Document  # type: ignore[import-not-found]

from riskagent_rag.config.settings import settings


_ANSWER_TEMPLATE_INSTRUCTIONS = (
    "Use the following markdown structure:\n"
    "1) TLDR (2-4 bullets)\n"
    "2) Concept (plain explanation)\n"
    "3) Why it matters (for risk systems)\n"
    "4) Data flow / fields (engineer facing)\n"
    "5) Example (short)\n"
    "6) Citations (list)\n"
)

_COMPLIANCE_INSTRUCTIONS = (
    "Compliance:\n"
    "- Do not output secrets, credentials, or personal data.\n"
    "- Do not provide trading or investment advice.\n"
    "- If the context is insufficient, say you do not know and propose next actions.\n"
    "- Do not invent numbers.\n"
)


def _format_context(docs: Iterable[Document], limit: int = 1200) -> str:
    # 将检索到的 Document 列表格式化成上下文文本.
    # 这里用 limit 做一个粗粒度截断, 避免 prompt 太长.
    # 技术难点: 这里的截断策略会影响.
    # - 生成质量(上下文不足)
    # - 延迟与成本(prompt 过长)
    # Week 2 可能需要更可控的策略, 例如按 score 或按 section 重要性拼接.
    parts: list[str] = []
    total = 0
    for i, d in enumerate(docs, start=1):
        meta = getattr(d, "metadata", {}) or {}
        expanded = ""
        if isinstance(meta, dict):
            expanded = str(meta.get("expanded_text") or "").strip()
        text = expanded or (d.page_content or "").strip()
        if not text:
            continue
        header = f"[ctx {i}]\n"
        footer = "\n"
        remaining = int(limit) - int(total)
        if remaining <= len(header) + len(footer):
            break
        max_text = remaining - len(header) - len(footer)
        chunk_text = text[:max_text]
        chunk = f"{header}{chunk_text}{footer}"
        parts.append(chunk)
        total += len(chunk)
        if total >= limit:
            break
    return "\n".join(parts).strip()


def call_llm_text(prompt: str, *, temperature: float = 0.0) -> str:
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key. Set OPENAI_API_KEY (or LLM_API_KEY).")

    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    llm = ChatOpenAI(
        model=settings.llm.model,
        base_url=settings.llm.base_url,
        api_key=api_key,
        temperature=float(temperature),
        default_headers=headers or None,
    )
    msg = llm.invoke(prompt)
    return getattr(msg, "content", str(msg))


def call_llm_json(prompt: str, *, temperature: float = 0.0) -> dict[str, Any]:
    text = call_llm_text(prompt, temperature=float(temperature))
    try:
        data = json.loads(str(text or ""))
    except Exception as exc:
        raise RuntimeError("LLM did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM returned JSON but not an object")
    return data


def generate_answer(question: str, docs: list[Document]) -> str:
    # 统一入口, 输入 question + docs, 输出 answer 字符串.
    # 注意: citations 的结构化输出在 pipeline.extract_citations 里实现.
    # 技术难点: answer 生成和 citations 展示是两个 contract.
    # - answer 必须尽量 grounded, 但 citations 不能依赖模型自述, 必须来自 retriever 的 metadata.
    # 业务不清晰点: 如果上下文不够.
    # - 是拒答.
    # - 还是给出不确定结论并提示补充语料.
    # 当前采用最保守策略, 上下文不足直接提示补资料.

    context = _format_context(docs)
    if not context:
        raise RuntimeError("No retrieval context available for answer generation")

    prompt = (
        "You are a helpful assistant explaining financial derivatives and risk concepts to software engineers. "
        "Answer using only the provided context.\n\n"
        f"{_COMPLIANCE_INSTRUCTIONS}\n"
        f"{_ANSWER_TEMPLATE_INSTRUCTIONS}\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )
    return call_llm_text(prompt, temperature=0.0)
