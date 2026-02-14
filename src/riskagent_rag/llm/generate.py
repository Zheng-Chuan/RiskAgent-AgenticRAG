"""LLM 输出生成.

这个模块提供一个极简的 LLM adapter.

目标.
- MVP 阶段优先保证可运行, 可演示.
- 如果用户配置了 API key, 则走真实模型生成.
- 如果没有配置 API key, 则直接报错并提示配置方式.

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
        raise RuntimeError(
            "Ollama call failed. Make sure ollama is running and OLLAMA_BASE_URL is correct."
        ) from exc

    try:
        data = json.loads(body)
    except Exception as exc:
        raise RuntimeError("Ollama returned non-JSON response") from exc

    text = str(data.get("response", "")).strip()
    if text:
        return text
    raise RuntimeError("Ollama returned empty response")


def call_llm_text(prompt: str, *, temperature: float = 0.0) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip() or "openai_compatible"
    if provider == "ollama":
        return _call_ollama_generate(prompt, options={"temperature": float(temperature)})

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM API key. Set OPENAI_API_KEY or LLM_API_KEY.")

    from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    base_url = os.getenv("LLM_BASE_URL")
    llm = ChatOpenAI(model=model, base_url=base_url or None, api_key=api_key, temperature=float(temperature))
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
