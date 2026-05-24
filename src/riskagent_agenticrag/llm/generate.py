"""LLM 输出生成 -- 统一封装 LLM 调用与 answer 生成."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Iterable

from langchain_core.documents import Document

from riskagent_agenticrag.config.settings import get_settings, settings
from riskagent_agenticrag.llm.governance import get_llm_cost_governor, LLMGovernanceError
from riskagent_agenticrag.llm.llm_cache import CachedResponse, LLMCache, get_llm_cache
from riskagent_agenticrag.llm.token_tracker import get_token_tracker

logger = logging.getLogger(__name__)

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
    timeout: int = 180,
) -> tuple[str, dict[str, int]]:
    """通过 curl 子进程调用 OpenAI 兼容 API (用于 n1n.ai 等特殊场景).

    Returns:
        Tuple of (content, usage_dict) where usage_dict has prompt_tokens
        and completion_tokens keys.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name
    try:
        cmd = [
            "curl", "-v", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", f"@{payload_file}",
            "--max-time", str(timeout),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=float(timeout + 5))
        if result.returncode != 0:
            stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise RuntimeError(f"curl failed (code {result.returncode})\nstdout: {stdout}\nstderr: {stderr}")
        raw_stdout = result.stdout.decode("utf-8", errors="replace")
        data = json.loads(raw_stdout)

        # Check for HTTP-level errors returned in the response body
        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            error_type = data["error"].get("type", "")
            raise RuntimeError(f"API error ({error_type}): {error_msg}")

        content = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        return content, {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
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
) -> tuple[str, dict[str, int]]:
    """通过 langchain_openai.ChatOpenAI 调用 LLM.

    Returns:
        Tuple of (content, usage_dict) where usage_dict has prompt_tokens
        and completion_tokens keys.
    """
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
    content = getattr(msg, "content", str(msg))

    # Extract token usage from response metadata if available
    usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
    resp_meta = getattr(msg, "response_metadata", None) or {}
    token_usage = resp_meta.get("token_usage") or resp_meta.get("usage", {})
    if token_usage:
        usage["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
        usage["completion_tokens"] = token_usage.get("completion_tokens", 0)

    return content, usage


_TRANSIENT_EXCEPTIONS = (
    subprocess.TimeoutExpired,
    ConnectionError,
    OSError,
    TimeoutError,
)


def _is_transient_error(exc: Exception) -> bool:
    """判断异常是否为可重试的瞬时错误."""
    if isinstance(exc, _TRANSIENT_EXCEPTIONS):
        return True
    msg = str(exc).lower()
    # HTTP 429 or 5xx status codes
    if "429" in msg or "rate limit" in msg:
        return True
    if any(f"{code}" in msg for code in range(500, 600)):
        return True
    if "timeout" in msg or "timed out" in msg or "connection" in msg:
        return True
    return False


def _call_llm_core(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    priority: str = "default",
    estimated_tokens: int | None = None,
) -> str:
    """LLM 调用统一入口, 自动选择 curl 或 langchain 路径.

    集成流量管理: 治理限流 → 缓存检查 → 带退避重试 → token 追踪 → 缓存写入.
    """
    gov_cfg = get_settings().llm_governance

    # --- (a) Governance check ---
    governor = get_llm_cost_governor()
    token_estimate = estimated_tokens or max_tokens or 1000
    allowed, meta = governor.allow(priority, token_estimate)
    if not allowed:
        raise LLMGovernanceError(meta)

    # --- Resolve model / key ---
    resolved_key = settings.llm.resolved_api_key
    if not resolved_key:
        raise RuntimeError("Missing API key. Set OPENAI_API_KEY (or LLM_API_KEY).")
    api_key = resolved_key.get_secret_value()

    resolved_model = model or settings.llm.model
    base_url = settings.llm.base_url or ""

    # --- (b) Cache check ---
    messages = [{"role": "user", "content": prompt}]
    resolved_max_tokens: int | None = max_tokens
    if not model and "n1n.ai" not in base_url:
        resolved_max_tokens = None

    cache = get_llm_cache()
    cache_key = LLMCache.make_key(messages, resolved_model, temperature, resolved_max_tokens)
    cached = cache.get(cache_key)
    if cached is not None:
        tracker = get_token_tracker()
        tracker.record(resolved_model, cached.prompt_tokens, cached.completion_tokens, 0.0, cached=True)
        return cached.content

    # --- (c) Retry with backoff ---
    max_retries = gov_cfg.max_retries
    backoff_base = gov_cfg.retry_backoff_base
    timeout_total = gov_cfg.timeout_total

    last_exc: Exception | None = None
    content: str = ""
    usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

    for attempt in range(max_retries):
        try:
            # --- (e) Measure latency ---
            t0 = time.time()

            if "n1n.ai" in base_url:
                payload: dict[str, Any] = {
                    "model": resolved_model,
                    "messages": messages,
                    "temperature": float(temperature),
                    "max_tokens": max_tokens,
                }
                if model is None and "qwen3" in resolved_model:
                    payload["enable_thinking"] = False
                content, usage = _call_via_curl(
                    f"{base_url}/chat/completions", api_key, payload, timeout=timeout_total,
                )
            else:
                content, usage = _call_via_langchain(
                    resolved_model, base_url, api_key, float(temperature),
                    resolved_max_tokens, prompt,
                )

            latency_ms = (time.time() - t0) * 1000.0
            break  # success

        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1 and _is_transient_error(exc):
                wait = backoff_base * (attempt + 1)
                logger.warning(
                    "LLM call attempt %d/%d failed (transient), retrying in %.1fs: %s",
                    attempt + 1, max_retries, wait, exc,
                )
                time.sleep(wait)
            else:
                raise
    else:
        # All retries exhausted (shouldn't reach here due to raise above, but safety net)
        if last_exc is not None:
            raise last_exc  # pragma: no cover

    # --- (d) Parse / estimate token usage ---
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    if prompt_tokens == 0 and completion_tokens == 0:
        # Fallback estimation
        prompt_tokens = len(str(messages)) // 4
        completion_tokens = len(content) // 4

    # --- (e) Record token usage ---
    tracker = get_token_tracker()
    tracker.record(resolved_model, prompt_tokens, completion_tokens, latency_ms, cached=False)

    # --- (f) Cache the response (deterministic only) ---
    if temperature == 0.0 or temperature is None:
        cache.put(cache_key, CachedResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=resolved_model,
            cached_at=time.time(),
        ))

    return content


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def call_llm_text(
    prompt: str,
    *,
    temperature: float = 0.0,
    priority: str = "default",
    estimated_tokens: int | None = None,
) -> str:
    """使用默认模型调用 LLM, 返回文本."""
    return _call_llm_core(
        prompt, temperature=temperature,
        priority=priority, estimated_tokens=estimated_tokens,
    )


def call_llm_json(
    prompt: str,
    *,
    temperature: float = 0.0,
    priority: str = "default",
    estimated_tokens: int | None = None,
) -> dict[str, Any]:
    """使用默认模型调用 LLM, 返回 JSON dict."""
    return _parse_json_response(call_llm_text(
        prompt, temperature=temperature,
        priority=priority, estimated_tokens=estimated_tokens,
    ))


def call_llm_text_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    priority: str = "default",
    estimated_tokens: int | None = None,
) -> str:
    """使用指定模型调用 LLM, 返回文本."""
    return _call_llm_core(
        prompt, model=model, temperature=temperature, max_tokens=max_tokens,
        priority=priority, estimated_tokens=estimated_tokens,
    )


def call_llm_json_with_model(
    prompt: str,
    *,
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    priority: str = "default",
    estimated_tokens: int | None = None,
) -> dict[str, Any]:
    """使用指定模型调用 LLM, 返回 JSON dict."""
    text = call_llm_text_with_model(
        prompt, model=model, temperature=temperature, max_tokens=max_tokens,
        priority=priority, estimated_tokens=estimated_tokens,
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
