from __future__ import annotations

from typing import Any

from riskagent_rag.config.settings import settings


def get_judge_llm() -> Any:
    api_key = settings.llm.api_key
    if api_key and (api_key.startswith("sk-") or len(api_key) > 10):
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.llm.model or "gpt-4o",
                api_key=api_key,
                base_url=settings.llm.base_url,
                temperature=0,
            )
        except ImportError:
            pass

    if settings.llm.provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama

            return ChatOllama(
                base_url=settings.llm.base_url or "http://localhost:11434",
                model=settings.llm.model or "qwen2.5:14b",
                temperature=0,
            )
        except ImportError:
            pass

    return None

