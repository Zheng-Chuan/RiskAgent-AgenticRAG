from __future__ import annotations

import os
from typing import Any

from riskagent_agenticrag.config.settings import get_settings, settings


def get_judge_llm() -> Any:
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key. Set OPENAI_API_KEY (or LLM_API_KEY).")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError("langchain-openai is required for judge llm") from exc

    headers: dict[str, str] = {}
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    title = os.getenv("OPENROUTER_APP_NAME", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    # 中文注释: citation judge 走独立 ChatOpenAI 实例, 这里也必须继承统一超时配置,
    # 否则全量 baseline 在收尾 judge 阶段可能无限等待远端响应.
    timeout_total = int(get_settings().llm_governance.timeout_total)
    return ChatOpenAI(
        model=settings.llm.model,
        api_key=api_key,
        base_url=settings.llm.base_url,
        temperature=0,
        timeout=float(timeout_total),
        default_headers=headers or None,
    )
