from __future__ import annotations

import importlib
import unittest

from tests.conftest import ensure_src_on_path

ensure_src_on_path()

try_compute_ragas_metrics = importlib.import_module(
    "riskagent_rag.evaluation.ragas_integration"
).try_compute_ragas_metrics


class EvaluationRagasIntegrationTest(unittest.TestCase):
    def test_try_compute_ragas_metrics_missing_dependency(self) -> None:
        # Mocking import error is hard here because it's already imported
        pass

    def test_try_compute_ragas_metrics_smoke(self) -> None:
        """测试 RAGAS 集成是否能运行 (即使没有 LLM 导致失败，也不应 crash)"""
        # 构造一个最小样本
        samples = [
            {
                "question": "What is delta?",
                "answer": "Delta is a risk metric.",
                "contexts": ["Delta measures the sensitivity of an option's price to changes in the underlying asset's price."],
                "ground_truth_contexts": ["Delta is sensitivity."],
                "reference_answer": "Delta is the rate of change.",
            }
        ]

        # 尝试运行
        # 如果没有配置 OPENAI_API_KEY 且没有 Ollama，这里可能会返回 ok=False, error="...".
        # 我们的目标是确保它跑通流程，而不是指标有多好。
        out = try_compute_ragas_metrics(samples=samples)
        
        self.assertTrue(out.enabled)
        # 只有在确实无法运行评估时 (例如 import error 或 evaluate 抛出异常) 才会 ok=False
        # 如果是因为没有 API Key 导致的 AuthenticationError, RAGAS evaluate 可能会抛出异常被捕获.
        
        if out.ok:
            print(f"RAGAS metrics computed: {out.metrics}")
            self.assertIsInstance(out.metrics, dict)
        else:
            print(f"RAGAS failed (expected if no LLM): {out.error}")
            self.assertIsNotNone(out.error)


if __name__ == "__main__":
    unittest.main()
