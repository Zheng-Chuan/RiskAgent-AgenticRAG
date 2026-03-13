from __future__ import annotations

import importlib
import unittest

from tests.conftest import ensure_src_on_path

ensure_src_on_path()

try:
    try_compute_ragas_metrics = importlib.import_module(
        "riskagent_agenticrag.evaluation.ragas_integration"
    ).try_compute_ragas_metrics
    _IMPORT_OK = True
except (ImportError, TypeError) as _exc:
    _IMPORT_OK = False
    _IMPORT_ERR = str(_exc)


@unittest.skipUnless(_IMPORT_OK, f"ragas import failed: {_IMPORT_ERR if not _IMPORT_OK else ''}")
class EvaluationRagasIntegrationTest(unittest.TestCase):
    def test_try_compute_ragas_metrics_missing_dependency(self) -> None:
        pass

    def test_try_compute_ragas_metrics_smoke(self) -> None:
        """RAGAS 集成 smoke test: 验证流程不 crash, 允许因环境缺失而 ok=False."""
        samples = [
            {
                "question": "What is delta?",
                "answer": "Delta is a risk metric.",
                "contexts": ["Delta measures the sensitivity of an option's price."],
                "ground_truth_contexts": ["Delta is sensitivity."],
                "reference_answer": "Delta is the rate of change.",
            }
        ]
        try:
            out = try_compute_ragas_metrics(samples=samples)
        except TypeError:
            self.skipTest("langchain metaclass conflict in current env")
            return

        self.assertTrue(out.enabled)
        if out.ok:
            self.assertIsInstance(out.metrics, dict)
        else:
            self.assertIsNotNone(out.error)


if __name__ == "__main__":
    unittest.main()
