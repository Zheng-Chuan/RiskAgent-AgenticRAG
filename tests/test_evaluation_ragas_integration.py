from __future__ import annotations

import unittest

from tests.conftest import ensure_src_on_path

a = ensure_src_on_path

ensure_src_on_path()

from riskagent_rag.evaluation.ragas_integration import try_compute_ragas_metrics


class EvaluationRagasIntegrationTest(unittest.TestCase):
    def test_try_compute_ragas_metrics_missing_dependency(self) -> None:
        out = try_compute_ragas_metrics(samples=[{"question": "q", "answer": "a", "contexts": ["c"]}])
        self.assertTrue(out.enabled)
        if out.ok:
            self.assertIsInstance(out.metrics, dict)
        else:
            self.assertIsNotNone(out.error)


if __name__ == "__main__":
    unittest.main()
