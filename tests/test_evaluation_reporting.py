from __future__ import annotations

import importlib
import unittest



citations_mod = importlib.import_module("riskagent_agenticrag.evaluation.citations")
compute_citations_coverage = citations_mod.compute_citations_coverage
is_valid_citation = citations_mod.is_valid_citation
compare_reports = importlib.import_module("riskagent_agenticrag.evaluation.reporting").compare_reports


class EvaluationReportingTest(unittest.TestCase):
    def test_is_valid_citation(self) -> None:
        self.assertTrue(is_valid_citation({"source": "corpus/Background.md", "chunk_id": "x"}))
        self.assertTrue(is_valid_citation({"source": "/tmp/corpus/Background.md", "chunk_id": "x"}))
        self.assertFalse(is_valid_citation({"source": "docs/Background.md", "chunk_id": "x"}))
        self.assertFalse(is_valid_citation({"source": "corpus/Background.md", "chunk_id": ""}))

    def test_compute_citations_coverage(self) -> None:
        samples = [
            {"citations": [{"source": "corpus/a.md", "chunk_id": "1"}]},
            {"citations": [{"source": "docs/a.md", "chunk_id": "1"}]},
            {"citations": []},
        ]
        cov = compute_citations_coverage(samples)
        self.assertEqual(cov.total, 3)
        self.assertEqual(cov.passed, 1)
        self.assertAlmostEqual(cov.coverage, 1 / 3)

    def test_compare_reports_regression(self) -> None:
        baseline = {"metrics": {"citations_coverage": 0.9}}
        current = {"metrics": {"citations_coverage": 0.8}}
        diff = compare_reports(current_report=current, baseline_report=baseline, tolerance=0.05, minimum=0.0)
        self.assertTrue(diff["citations_coverage"]["regression"])


if __name__ == "__main__":
    unittest.main()
