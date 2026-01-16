# 中文注释: LangGraph 验收测试
# 用途: 验证 LangGraph runner 与纯函数 runner 的输出 schema 一致性

import os
import sys
import unittest
import importlib
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

# 中文注释: 确保 src 在 sys.path 中, 便于导入项目模块
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

run_langgraph_agentic_chat = importlib.import_module(
    "riskagent_rag.orchestration.langgraph_runner"
).run_langgraph_agentic_chat
run_agentic_chat = importlib.import_module("riskagent_rag.rag.agentic_loop").run_agentic_chat


class ContractLangGraphTest(unittest.TestCase):
    """LangGraph 验收测试."""

    def test_langgraph_output_schema_matches_pure_function(self):
        """测试 LangGraph runner 输出 schema 与纯函数 runner 一致."""
        os.environ["LLM_PROVIDER"] = "fallback"

        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        question = "What is delta?"
        max_rounds = 1

        pure_out = run_agentic_chat(question=question, retriever=mock_retriever, max_rounds=max_rounds)
        langgraph_out = run_langgraph_agentic_chat(question=question, retriever=mock_retriever, max_rounds=max_rounds)

        self.assertIn("answer", pure_out)
        self.assertIn("answer", langgraph_out)

        self.assertIn("docs", pure_out)
        self.assertIn("docs", langgraph_out)

        self.assertIn("citations", pure_out)
        self.assertIn("citations", langgraph_out)

        self.assertIn("decision_log", pure_out)
        self.assertIn("decision_log", langgraph_out)

        self.assertIn("tool_traces", pure_out)
        self.assertIn("tool_traces", langgraph_out)

        self.assertIn("claims", pure_out)
        self.assertIn("claims", langgraph_out)

        self.assertIn("evidence_set", pure_out)
        self.assertIn("evidence_set", langgraph_out)

        self.assertIn("status", pure_out)
        self.assertIn("status", langgraph_out)

        self.assertIn("failure_reason", pure_out)
        self.assertIn("failure_reason", langgraph_out)

        self.assertIn("debug", pure_out)
        self.assertIn("debug", langgraph_out)

        self.assertIsInstance(pure_out["answer"], str)
        self.assertIsInstance(langgraph_out["answer"], str)

        self.assertIsInstance(pure_out["citations"], list)
        self.assertIsInstance(langgraph_out["citations"], list)

        self.assertIsInstance(pure_out["decision_log"], list)
        self.assertIsInstance(langgraph_out["decision_log"], list)

        self.assertIsInstance(pure_out["tool_traces"], list)
        self.assertIsInstance(langgraph_out["tool_traces"], list)

        self.assertIsInstance(pure_out["claims"], list)
        self.assertIsInstance(langgraph_out["claims"], list)

        self.assertIsInstance(pure_out["evidence_set"], list)
        self.assertIsInstance(langgraph_out["evidence_set"], list)

        self.assertIn(pure_out["status"], ["ok", "failed"])
        self.assertIn(langgraph_out["status"], ["ok", "failed"])

    def test_langgraph_decision_log_structure(self):
        """测试 LangGraph runner 的 decision_log 结构."""
        os.environ["LLM_PROVIDER"] = "fallback"

        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        question = "What is delta?"
        max_rounds = 1

        out = run_langgraph_agentic_chat(question=question, retriever=mock_retriever, max_rounds=max_rounds)

        decision_log = out["decision_log"]
        self.assertIsInstance(decision_log, list)
        self.assertGreater(len(decision_log), 0)

        for decision in decision_log:
            self.assertIn("step_id", decision)
            self.assertIn("agent", decision)
            self.assertIn("rationale", decision)
            self.assertIn("chosen", decision)
            self.assertIn("alternatives", decision)

    def test_langgraph_with_ollama_env(self):
        """测试 LangGraph runner 在 Ollama 环境下的行为."""
        original_provider = os.getenv("LLM_PROVIDER")
        os.environ["LLM_PROVIDER"] = "ollama"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        os.environ["OLLAMA_MODEL"] = "qwen3:8b"

        try:
            mock_retriever = MagicMock()
            mock_retriever.invoke.return_value = []

            question = "What is delta?"
            max_rounds = 1

            out = run_langgraph_agentic_chat(question=question, retriever=mock_retriever, max_rounds=max_rounds)

            self.assertIn("answer", out)
            self.assertIn("status", out)
            self.assertIn("decision_log", out)

            self.assertIsInstance(out["answer"], str)
            self.assertGreater(len(out["decision_log"]), 0)
        finally:
            if original_provider:
                os.environ["LLM_PROVIDER"] = original_provider
            else:
                os.environ.pop("LLM_PROVIDER", None)

    def test_langgraph_respects_max_rounds_for_retrieval(self):
        os.environ["LLM_PROVIDER"] = "fallback"

        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []

        with patch(
            "riskagent_rag.rag.agentic_primitives.critique_retrieval",
            return_value=(False, "improved query", "insufficient"),
        ):
            _out = run_langgraph_agentic_chat(
                question="What is delta?",
                retriever=mock_retriever,
                max_rounds=2,
            )

        self.assertEqual(mock_retriever.invoke.call_count, 2)


if __name__ == "__main__":
    unittest.main()
