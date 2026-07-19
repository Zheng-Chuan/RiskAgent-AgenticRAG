from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_call_llm_json_parses_fenced_json() -> None:
    from riskagent_agenticrag.llm.generate import call_llm_json

    fenced = '```json\n{"sufficient": true, "reason": "ok"}\n```'
    with patch("riskagent_agenticrag.llm.generate.call_llm_text", return_value=fenced):
        result = call_llm_json("prompt")

    assert result == {"sufficient": True, "reason": "ok"}


@pytest.mark.unit
def test_call_llm_json_repairs_non_json_output() -> None:
    from riskagent_agenticrag.llm.generate import call_llm_json

    with patch(
        "riskagent_agenticrag.llm.generate.call_llm_text",
        side_effect=[
            "Here is the result: sufficient yes",
            '{"sufficient": false, "improved_query": "frtb capital", "reason": "repair"}',
        ],
    ):
        result = call_llm_json("prompt")

    assert result["sufficient"] is False
    assert result["improved_query"] == "frtb capital"


@pytest.mark.unit
def test_call_via_langchain_passes_timeout() -> None:
    from riskagent_agenticrag.llm.generate import _call_via_langchain

    class _FakeMessage:
        content = '{"ok": true}'
        response_metadata = {"token_usage": {"prompt_tokens": 1, "completion_tokens": 2}}

    class _FakeChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def invoke(self, prompt: str):
            assert prompt == "prompt"
            assert float(self.kwargs["timeout"]) == 42.0
            return _FakeMessage()

    with patch("langchain_openai.ChatOpenAI", _FakeChatOpenAI):
        content, usage = _call_via_langchain(
            model="test-model",
            base_url="https://example.com/v1",
            api_key="secret",
            temperature=0.0,
            max_tokens=None,
            timeout_total=42,
            prompt="prompt",
        )

    assert content == '{"ok": true}'
    assert usage == {"prompt_tokens": 1, "completion_tokens": 2}


@pytest.mark.unit
def test_sanitize_answer_removes_refusal_style_meta_lines() -> None:
    from riskagent_agenticrag.llm.generate import _sanitize_answer_for_grounding

    answer = (
        "1) TLDR\n"
        "- The provided context does not specify when FRTB was finalized.\n"
        "- FRTB is a market risk framework.\n\n"
        "Here are suggested next steps:\n"
        "- Search another source.\n"
    )

    cleaned = _sanitize_answer_for_grounding(answer)

    assert "provided context does not specify" not in cleaned.lower()
    assert "suggested next steps" not in cleaned.lower()
    assert "FRTB is a market risk framework." in cleaned
