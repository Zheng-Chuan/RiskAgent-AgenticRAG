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

import json
import os
import urllib.error
import urllib.request
from typing import Any, Iterable, Optional

from langchain_core.documents import Document  # type: ignore[import-not-found]


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
        text = (d.page_content or "").strip()
        if not text:
            continue
        chunk = f"[ctx {i}]\n{text}\n"
        total += len(chunk)
        if total > limit:
            break
        parts.append(chunk)
    return "\n".join(parts).strip()


def _call_ollama_generate(
    prompt: str,
    *,
    response_format: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
) -> str:
    # 中文注释: 通过 Ollama 本地 HTTP API 调用模型, 便于本地开发实时看到效果.
    # 约定.
    # - OLLAMA_BASE_URL: 默认 http://localhost:11434
    # - OLLAMA_MODEL: 默认 llama3.1:8b
    # - OLLAMA_TIMEOUT_SECONDS: 默认 60
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

    url = f"{base_url}/api/generate"
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    if response_format:
        # 中文注释: Ollama 支持 format=json, 适合让模型输出结构化内容.
        payload["format"] = response_format

    if options:
        payload["options"] = options

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return (
            "Ollama call failed. "
            "Make sure ollama is running and OLLAMA_BASE_URL is correct. "
            f"error={exc}"
        )

    try:
        data = json.loads(body)
    except Exception as exc:
        return f"Ollama returned non-JSON response. error={exc} body={body[:400]}"

    text = str(data.get("response", "")).strip()
    if text:
        return text
    return f"Ollama returned empty response. body={body[:400]}"


def generate_answer(question: str, docs: list[Document]) -> str:
    # 统一入口, 输入 question + docs, 输出 answer 字符串.
    # 注意: citations 的结构化输出在 pipeline.extract_citations 里实现.
    # 技术难点: answer 生成和 citations 展示是两个 contract.
    # - answer 必须尽量 grounded, 但 citations 不能依赖模型自述, 必须来自 retriever 的 metadata.
    # 业务不清晰点: 如果上下文不够.
    # - 是拒答.
    # - 还是给出不确定结论并提示补充语料.
    # 当前采用最保守策略, 上下文不足直接提示补资料.

    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider == "ollama":
        context = _format_context(docs)
        prompt = (
            "You are a helpful assistant explaining financial derivatives and risk concepts to software engineers. "
            "Answer using only the provided context. If context is insufficient, say you do not know. "
            "Keep the answer concise and include next actions when refusing.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n"
        )
        return _call_ollama_generate(prompt)

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if api_key:
        # 有 key 时, 使用 langchain_openai 的 ChatOpenAI.
        # base_url 支持 OpenAI compatible API, 便于后续接入不同大模型服务.
        # 技术难点: OpenAI compatible server 的字段和行为可能不完全一致.
        # - streaming, tool calling, max tokens, error schema
        # MVP 先使用最小可用接口, Week 2 再逐步增强.
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

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
        # 技术难点: prompt injection 与越权引用.
        # - 这里要求只使用 context, 但模型仍可能编造.
        # Week 2 需要在 eval 中加入 groundedness 检查.
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
