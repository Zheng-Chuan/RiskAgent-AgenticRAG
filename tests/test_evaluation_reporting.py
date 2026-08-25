from __future__ import annotations

import importlib
import tempfile
import unittest

citations_mod = importlib.import_module("riskagent_agenticrag.evaluation.citations")
compute_citations_coverage = citations_mod.compute_citations_coverage
is_valid_citation = citations_mod.is_valid_citation
compare_reports = importlib.import_module("riskagent_agenticrag.evaluation.reporting").compare_reports
write_report = importlib.import_module("riskagent_agenticrag.evaluation.reporting").write_report
load_report = importlib.import_module("riskagent_agenticrag.evaluation.reporting").load_report


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
        self.assertTrue(diff["comparisons"]["citations_coverage"]["baseline_regression"])

    def test_compare_reports_lower_is_better_improvement_not_regression(self) -> None:
        """contradiction_score 属 lower-is-better, 下降是改善不应判回归 (v10e 误判案例)."""
        baseline = {"metrics": {"contradiction_score": 0.022}}
        current = {"metrics": {"contradiction_score": 0.0}}
        diff = compare_reports(current_report=current, baseline_report=baseline, tolerance=0.0, minimum=0.0)
        self.assertFalse(diff["comparisons"]["contradiction_score"]["baseline_regression"])

    def test_compare_reports_lower_is_better_increase_is_regression(self) -> None:
        """contradiction_score 上升是真回归."""
        baseline = {"metrics": {"contradiction_score": 0.0}}
        current = {"metrics": {"contradiction_score": 0.05}}
        diff = compare_reports(current_report=current, baseline_report=baseline, tolerance=0.0, minimum=0.0)
        self.assertTrue(diff["comparisons"]["contradiction_score"]["baseline_regression"])

    def test_compare_reports_sentence_support_rate_is_higher_better(self) -> None:
        """sentence_support_rate 以 _rate 结尾但属 higher-is-better, 上升不应判回归 (v10e 误判案例)."""
        baseline = {"metrics": {"sentence_support_rate": 0.828}}
        current = {"metrics": {"sentence_support_rate": 0.858}}
        diff = compare_reports(current_report=current, baseline_report=baseline, tolerance=0.0, minimum=0.0)
        self.assertFalse(diff["comparisons"]["sentence_support_rate"]["baseline_regression"])

    def test_write_report_keeps_gold_and_slice_retrieval_metrics(self) -> None:
        report = {
            "metrics": {"retrieval_recall_at_5": 0.8},
            "retrieval_metrics": {
                "gold_metrics": {"retrieval_recall_at_5": 0.8},
                "slice_metrics": {"definition": {"retrieval_recall_at_5": 1.0}},
                "citation_diagnostics": {"citations_coverage": 0.5},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = write_report(report, artifacts_dir=td, label="m2")
            loaded = load_report(path)
        retrieval = loaded["retrieval_metrics"]
        self.assertIn("gold_metrics", retrieval)
        self.assertIn("slice_metrics", retrieval)
        self.assertIn("citation_diagnostics", retrieval)
        self.assertEqual(retrieval["slice_metrics"]["definition"]["retrieval_recall_at_5"], 1.0)


if __name__ == "__main__":
    unittest.main()
