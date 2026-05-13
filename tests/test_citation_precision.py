from __future__ import annotations

import os
import unittest


class Week6CitationPrecisionQualityTest(unittest.TestCase):
    def test_heuristic_citation_precision(self) -> None:
        from riskagent_agenticrag.evaluation.citation_precision import try_compute_citation_precision

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
        self.assertTrue(out.ok)
        self.assertGreaterEqual(float(out.metrics.get("citation_precision", 0.0)), 0.99)
        self.assertEqual(out.details[0]["unsupported_sentences"], [])

    def test_heuristic_hallucination_rate(self) -> None:
        from riskagent_agenticrag.evaluation.citation_precision import try_compute_citation_precision

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
        self.assertGreater(float(out.metrics.get("hallucination_rate_in_citations", 0.0)), 0.0)
        self.assertGreater(float(out.metrics.get("unsupported_sentence_rate", 0.0)), 0.0)
        unsupported = [row for row in out.details if row["id"] == "unsupported"][0]
        self.assertTrue(unsupported["unsupported_sentences"])
