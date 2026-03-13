"""LLM 输出生成 -- 统一封装 LLM 调用与 answer 生成."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Any, Iterable

from langchain_core.documents import Document

from riskagent_agenticrag.config.settings import settings

# ---- prompt 模板片段 ----

_ANSWER_TEMPLATE_INSTRUCTIONS = (
    "Use the following markdown structure:\n"
    "1) TLDR (2-4 bullets, each grounded in context)\n"
    "2) Key Facts (only facts explicitly stated in context)\n"
    "3) Why it matters (only if context discusses relevance)\n"
    "Do NOT include sections for which the context provides no information.\n"
    "Do NOT generate examples unless the context contains one.\n"
)

_COMPLIANCE_INSTRUCTIONS = (
    "STRICT COMPLIANCE:\n"
    "- Every number in your answer MUST appear verbatim in the provided context.\n"
    "- Do NOT infer, calculate, or fabricate any number not explicitly stated in context.\n"
    "- If context is insufficient, say you do not know and propose next actions.\n"
    "- Do not output secrets, credentials, or personal data.\n"
    "- Do not provide trading or investment advice.\n"
)


# ---------------------------------------------------------------------------
# 内部: 统一 LLM 调用核心
# ---------------------------------------------------------------------------

def _call_via_curl(
    url: str,
    api_key: str,
    payload: dict[str, Any],
) -> str:
    """通过 curl 子进程调用 OpenAI 兼容 API (用于 n1n.ai 等特殊场景)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name
    try:
        cmd = [
            "curl", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", f"@{payload_file}",
            "--max-time", "180",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=185.0)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise RuntimeError(f"curl failed (code {result.returncode}): {stderr}")
        data = json.loads(result.stdout.decode("utf-8", errors="replace"))
        return data["choices"][0]["message"]["content"] or ""
    finally:
        try:
            os.unlink(payload_file)
        except OSError:
            pass


def _call_via_langchain(
    model: str,
    base_url: str,
    api_key: str,
    temperature: float,
    max_tokens: int | None,
    prompt: str,
) -> str:
    """通过 langchain_openai.ChatOpenAI 调用 LLM."""
    from langchain_openai import ChatOpenAI

    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    kwargs: dict[str, Any] = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "temperature": temperature,
        "default_headers": headers or None,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    msg = ChatOpenAI(**kwargs).invoke(prompt)
    return getattr(msg, "content", str(msg))


def _call_llm_core(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """LLM 调用统一入口, 自动选择 curl 或 langchain 路径."""
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing API key. Set OPENAI_API_KEY (or LLM_API_KEY).")

    resolved_model = model or settings.llm.model
    base_url = settings.llm.base_url or ""

    # n1n.ai 兼容: 通过 curl 子进程调用
    if "n1n.ai" in base_url:
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": max_tokens,
        }
        if model is None and "qwen3" in resolved_model:
            payload["enable_thinking"] = False
        return _call_via_curl(f"{base_url}/chat/completions", api_key, payload)

    return _call_via_langchain(
        resolved_model, base_url, api_key, float(temperature),
        max_tokens if model else None, prompt,
    )


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def call_llm_text(prompt: str, *, temperature: float = 0.0) -> str:
    """使用默认模型调用 LLM, 返回文本."""
    return _call_llm_core(prompt, temperature=temperature)


def call_llm_json(prompt: str, *, temperature: float = 0.0) -> dict[str, Any]:
    """使用默认模型调用 LLM, 返回 JSON dict."""
    return _parse_json_response(call_llm_text(prompt, temperature=temperature))


def call_llm_text_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """使用指定模型调用 LLM, 返回文本."""
    return _call_llm_core(
        prompt, model=model, temperature=temperature, max_tokens=max_tokens,
    )


def call_llm_json_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """使用指定模型调用 LLM, 返回 JSON dict."""
    text = call_llm_text_with_model(
        prompt, model=model, temperature=temperature, max_tokens=max_tokens,
    )
    return _parse_json_response(text)


# ---------------------------------------------------------------------------
# answer 生成
# ---------------------------------------------------------------------------

def _format_context(docs: Iterable[Document], limit: int = 1200) -> str:
    """将检索到的 Document 列表格式化为上下文文本, 按 limit 粗粒度截断."""
    parts: list[str] = []
    total = 0
    for i, d in enumerate(docs, start=1):
        meta = getattr(d, "metadata", {}) or {}
        expanded = str(meta.get("expanded_text") or "").strip() if isinstance(meta, dict) else ""
        text = expanded or (d.page_content or "").strip()
        if not text:
            continue
        header = f"[ctx {i}]\n"
        footer = "\n"
        remaining = limit - total
        if remaining <= len(header) + len(footer):
            break
        chunk_text = text[: remaining - len(header) - len(footer)]
        parts.append(f"{header}{chunk_text}{footer}")
        total += len(header) + len(chunk_text) + len(footer)
        if total >= limit:
            break
    return "\n".join(parts).strip()


def generate_answer(question: str, docs: list[Document]) -> str:
    """统一入口: question + docs -> answer 字符串."""
    context = _format_context(docs)
    if not context:
        raise RuntimeError("No retrieval context available for answer generation")
    prompt = (
        "You are a precise assistant explaining financial derivatives and risk concepts. "
        "Answer STRICTLY using only facts from the provided context. "
        "Do NOT add information beyond what the context explicitly states.\n\n"
        f"{_COMPLIANCE_INSTRUCTIONS}\n"
        f"{_ANSWER_TEMPLATE_INSTRUCTIONS}\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )
    return call_llm_text(prompt, temperature=0.0)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON 文本, 校验为 dict."""
    try:
        data = json.loads(str(text or ""))
    except Exception as exc:
        raise RuntimeError("LLM did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM returned JSON but not an object")
    return data
