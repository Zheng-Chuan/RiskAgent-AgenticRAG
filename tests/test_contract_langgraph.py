import unittest
from unittest.mock import MagicMock, patch

from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat


class ContractLangGraphTest(unittest.TestCase):
    def _fake_llm_json(self, prompt: str, temperature: float = 0.0):
        p = str(prompt or "")
        if "\"query\"" in p and "Schema" in p:
            return {"query": "delta definition"}
        if "\"sufficient\"" in p and "Schema" in p:
            return {"sufficient": True, "improved_query": "", "reason": "ok"}
        return {}

    def _fake_llm_text(self, prompt: str, temperature: float = 0.0):
        return "ok"

    def test_langgraph_output_schema(self):
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        question = "What is delta?"
        max_rounds = 1

        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=self._fake_llm_text
        ), patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=self._fake_llm_text):
            out = run_langgraph_agentic_chat(question=question, retriever=mock_retriever, max_rounds=max_rounds)

        for k in ("answer", "docs", "citations", "decision_log", "claims", "evidence_set", "status", "failure_reason", "debug"):
            self.assertIn(k, out)
        self.assertNotIn("tool_traces", out)

        self.assertIsInstance(out["answer"], str)
        self.assertIsInstance(out["citations"], list)
        self.assertIsInstance(out["decision_log"], list)
        self.assertIsInstance(out["claims"], list)
        self.assertIsInstance(out["evidence_set"], list)
        self.assertIn(out["status"], ["ok", "failed"])

    def test_langgraph_decision_log_structure(self):
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=self._fake_llm_text
        ), patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=self._fake_llm_text):
            out = run_langgraph_agentic_chat(question="What is delta?", retriever=mock_retriever, max_rounds=1)

        decision_log = out["decision_log"]
        self.assertIsInstance(decision_log, list)
        self.assertGreater(len(decision_log), 0)

        for decision in decision_log:
            self.assertIn("step_id", decision)
            self.assertIn("agent", decision)
            self.assertIn("rationale", decision)
            self.assertIn("chosen", decision)
            self.assertIn("alternatives", decision)

    def test_langgraph_respects_max_rounds_for_retrieval(self):
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.critique_retrieval",
            return_value=(False, "improved query", "insufficient"),
        ), patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=self._fake_llm_text
        ), patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=self._fake_llm_text):
            _out = run_langgraph_agentic_chat(question="What is delta?", retriever=mock_retriever, max_rounds=2)

        self.assertEqual(mock_retriever.invoke.call_count, 2)


if __name__ == "__main__":
    unittest.main()
