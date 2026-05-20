from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from riskagent_agenticrag.agents.data_agent import extract_structured_request, run_data_agent
from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat


class NumericToolUseIntegrationTest(unittest.TestCase):
    def _fake_llm_json(self, prompt: str, temperature: float = 0.0):
        p = str(prompt or "")
        if "\"query\"" in p and "Schema" in p:
            return {"query": "desk exposure total delta breach"}
        if "\"sufficient\"" in p and "Schema" in p:
            return {"sufficient": True, "improved_query": "", "reason": "ok"}
        return {}

    def _build_retriever(self) -> MagicMock:
        retriever = MagicMock()
        retriever.invoke.return_value = [
            Document(
                page_content="Desk exposure governance requires checking total delta against the abs delta limit.",
                metadata={
                    "source": "corpus/test.md",
                    "chunk_id": "chunk_0",
                    "start_index": 0,
                },
            )
        ]
        return retriever

    def test_numeric_tool_trace_supports_matching_answer(self) -> None:
        question = "For desk EQD1 as of 2026-01-15 with abs delta limit 100000 what is the total delta and is there a breach"
        req = extract_structured_request(question=question, request_id="r1")
        self.assertIsNotNone(req)
        tool_output, _trace, failure = run_data_agent(req)
        self.assertIsNone(failure)
        expected_delta = float(tool_output["exposure"]["total_delta"])

        retriever = self._build_retriever()
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.synthesize_answer",
            return_value=f"Total delta equals {expected_delta:.2f} computed from the desk snapshot.",
        ):
            out = run_langgraph_agentic_chat(question=question, retriever=retriever, max_rounds=1)

        self.assertEqual(out["status"], "ok")
        debug = out.get("debug") or {}
        self.assertEqual(debug.get("tool_traces_count"), 1)
        self.assertEqual((debug.get("numeric_tool") or {}).get("invoked"), True)

    def test_numeric_tool_trace_blocks_mismatched_answer(self) -> None:
        question = "For desk EQD1 as of 2026-01-15 with abs delta limit 100000 what is the total delta and is there a breach"
        req = extract_structured_request(question=question, request_id="r1")
        self.assertIsNotNone(req)
        tool_output, _trace, failure = run_data_agent(req)
        self.assertIsNone(failure)
        wrong_delta = float(tool_output["exposure"]["total_delta"]) + 12345.0

        retriever = self._build_retriever()
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.synthesize_answer",
            return_value=f"Total delta equals {wrong_delta:.2f} computed from the desk snapshot.",
        ):
            out = run_langgraph_agentic_chat(question=question, retriever=retriever, max_rounds=1)

        self.assertEqual(out["status"], "failed")
        self.assertIn(
            (out.get("failure_reason") or {}).get("category"),
            {"evidence_numeric_mismatch", "numeric_calculated_mismatch"},
        )


if __name__ == "__main__":
    unittest.main()
