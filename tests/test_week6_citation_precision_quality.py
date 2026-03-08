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

        with self.assertRaises(ValueError):
            _ = try_compute_citation_precision(samples=samples, mode="heuristic")

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

        with self.assertRaises(ValueError):
            _ = try_compute_citation_precision(samples=samples, mode="heuristic")
