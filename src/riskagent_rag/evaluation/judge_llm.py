from __future__ import annotations

from typing import Any

from riskagent_rag.config.settings import settings


def get_judge_llm() -> Any:
    api_key = settings.llm.api_key
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key. Set OPENAI_API_KEY (or LLM_API_KEY).")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError("langchain-openai is required for judge llm") from exc

    return ChatOpenAI(
        model=settings.llm.model,
        api_key=api_key,
        base_url=settings.llm.base_url,
        temperature=0,
    )
