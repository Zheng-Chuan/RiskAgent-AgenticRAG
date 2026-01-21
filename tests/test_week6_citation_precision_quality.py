from __future__ import annotations

import os
import unittest

from tests.conftest import ensure_src_on_path


class Week6CitationPrecisionQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def test_heuristic_citation_precision(self) -> None:
        from riskagent_rag.evaluation.citation_precision import try_compute_citation_precision

        os.environ["EVAL_CITATION_JUDGE_MODE"] = "heuristic"

        samples = [
            {
                "id": "s1",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            }
        ]

        out = try_compute_citation_precision(samples=samples, mode="heuristic")
        self.assertTrue(out.enabled)
        self.assertTrue(out.ok)
        self.assertGreaterEqual(float(out.metrics.get("citation_precision", 0.0)), 0.99)
        self.assertLessEqual(float(out.metrics.get("hallucination_rate_in_citations", 1.0)), 0.01)

    def test_heuristic_hallucination_rate(self) -> None:
        from riskagent_rag.evaluation.citation_precision import try_compute_citation_precision

        os.environ["EVAL_CITATION_JUDGE_MODE"] = "heuristic"

        samples = [
            {
                "id": "supported",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            },
            {
                "id": "unsupported",
                "question": "What is FRTB?",
                "answer": "FRTB was published in 2099.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            },
        ]

        out = try_compute_citation_precision(samples=samples, mode="heuristic")
        self.assertTrue(out.ok)
        self.assertAlmostEqual(float(out.metrics.get("hallucination_rate_in_citations", 0.0)), 0.5, delta=1e-6)

