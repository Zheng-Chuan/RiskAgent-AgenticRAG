from __future__ import annotations

import importlib
import unittest

mod = importlib.import_module("riskagent_agenticrag.evaluation.advanced_metrics")
bootstrap_mean_ci = mod.bootstrap_mean_ci
compute_confidence_intervals = mod.compute_confidence_intervals

thresholds_mod = importlib.import_module("riskagent_agenticrag.evaluation.thresholds")
evaluate_threshold_gate = thresholds_mod.evaluate_threshold_gate


def _sample_with_support(
    *,
    status: str = "ok",
    supported: int = 2,
    total: int = 3,
    precision: float = 0.9,
    numeric_score: float = 1.0,
    valid_citation_count: int = 1,
) -> dict:
    return {
        "status": status,
        "valid_citation_count": valid_citation_count,
        "sentence_support": {
            "total_sentences": total,
            "supported_sentences_count": supported,
            "citation_precision": precision,
        },
        "domain_consistency": {"numeric": {"score": numeric_score}},
    }


class BootstrapMeanCiTest(unittest.TestCase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(bootstrap_mean_ci([]))

    def test_single_value_degenerate_ci(self) -> None:
        out = bootstrap_mean_ci([0.7])
        self.assertIsNotNone(out)
        self.assertEqual(out["mean"], 0.7)
        self.assertEqual(out["ci_low"], 0.7)
        self.assertEqual(out["ci_high"], 0.7)
        self.assertEqual(out["n"], 1.0)

    def test_constant_series_ci_collapses_to_value(self) -> None:
        out = bootstrap_mean_ci([0.5, 0.5, 0.5, 0.5])
        self.assertEqual(out["mean"], 0.5)
        self.assertEqual(out["ci_low"], 0.5)
        self.assertEqual(out["ci_high"], 0.5)

    def test_deterministic_with_fixed_seed(self) -> None:
        values = [0.1, 0.4, 0.9, 0.2, 0.6, 0.3, 0.8, 0.5, 0.7, 0.2]
        a = bootstrap_mean_ci(values, n_boot=200, seed=42)
        b = bootstrap_mean_ci(values, n_boot=200, seed=42)
        self.assertEqual(a, b)

    def test_ci_brackets_point_mean(self) -> None:
        values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.3, 0.7]
        out = bootstrap_mean_ci(values, n_boot=1000)
        self.assertLessEqual(out["ci_low"], out["mean"] + 1e-9)
        self.assertGreaterEqual(out["ci_high"], out["mean"] - 1e-9)
        self.assertLessEqual(out["ci_low"], out["ci_high"])
        self.assertEqual(out["n"], float(len(values)))

    def test_n_boot_zero_falls_back_to_degenerate(self) -> None:
        out = bootstrap_mean_ci([0.2, 0.8], n_boot=0)
        self.assertEqual(out["ci_low"], out["mean"])
        self.assertEqual(out["ci_high"], out["mean"])

    def test_none_values_are_skipped(self) -> None:
        out = bootstrap_mean_ci([None, 0.5, None, 0.5])
        self.assertEqual(out["n"], 2.0)
        self.assertEqual(out["mean"], 0.5)


class ComputeConfidenceIntervalsTest(unittest.TestCase):
    def test_series_keys_match_report_metric_names(self) -> None:
        samples = [
            {
                "status": "ok",
                "valid_citation_count": 1,
                "qrels": [{"qrel_id": "q1", "chunk_id": "a1", "text": "delta", "relevance": 2}],
                "retrieved_docs": [
                    {"source": "corpus/a.md", "chunk_id": "a1", "content": "delta definition", "dense_rank": 1},
                ],
            },
            {
                "status": "failed",
                "failure_reason": {"code": "E_GATE"},
                "valid_citation_count": 0,
                "qrels": [{"qrel_id": "q2", "text": "gamma", "relevance": 2}],
                "retrieved_docs": [
                    {"source": "corpus/b.md", "chunk_id": "b1", "content": "unrelated", "dense_rank": 1},
                ],
            },
        ]
        out = compute_confidence_intervals(samples=samples, ks=[1, 3], n_boot=100)
        self.assertIn("retrieval_mrr", out)
        self.assertIn("retrieval_recall_at_1", out)
        self.assertIn("retrieval_ndcg_at_3", out)
        self.assertIn("citations_coverage", out)
        self.assertIn("gate_block_rate", out)
        # 键名不带前缀, 与 report["metrics"] 对齐供 gate 查找
        for key in out:
            self.assertFalse(key.startswith("retrieval::"))
        self.assertEqual(out["citations_coverage"]["mean"], 0.5)
        self.assertEqual(out["gate_block_rate"]["mean"], 0.5)

    def test_sentence_support_and_precision_series(self) -> None:
        samples = [
            _sample_with_support(supported=3, total=3, precision=1.0),
            _sample_with_support(supported=1, total=2, precision=0.5),
        ]
        out = compute_confidence_intervals(samples=samples, ks=[1], n_boot=100)
        self.assertIn("sentence_support_rate", out)
        self.assertAlmostEqual(out["sentence_support_rate"]["mean"], (1.0 + 0.5) / 2)
        self.assertIn("citation_precision", out)
        self.assertAlmostEqual(out["citation_precision"]["mean"], 0.75)

    def test_numeric_consistency_series(self) -> None:
        samples = [
            _sample_with_support(numeric_score=1.0),
            _sample_with_support(numeric_score=0.5),
            _sample_with_support(numeric_score=0.0),
        ]
        out = compute_confidence_intervals(samples=samples, ks=[1], n_boot=100)
        self.assertIn("numeric_consistency_score", out)
        self.assertAlmostEqual(out["numeric_consistency_score"]["mean"], 0.5)

    def test_missing_details_omit_series(self) -> None:
        samples = [{"status": "ok", "valid_citation_count": 1}]
        out = compute_confidence_intervals(samples=samples, ks=[1], n_boot=10)
        self.assertNotIn("sentence_support_rate", out)
        self.assertNotIn("citation_precision", out)
        self.assertNotIn("numeric_consistency_score", out)
        self.assertIn("citations_coverage", out)

    def test_citations_fallback_to_citation_list_check(self) -> None:
        samples = [
            {
                "status": "ok",
                "citations": [{"source": "corpus/a.md", "chunk_id": "a1"}],
            },
            {
                "status": "ok",
                "citations": [{"source": "outside.md", "chunk_id": "x1"}],
            },
        ]
        out = compute_confidence_intervals(samples=samples, ks=[1], n_boot=10)
        self.assertEqual(out["citations_coverage"]["mean"], 0.5)


class ThresholdGateCiTest(unittest.TestCase):
    def test_gate_uses_ci_low_conservative_bound(self) -> None:
        # 点估计 0.85 过阈值, 但 ci_low=0.55 低于 minimum=0.6 → fail
        report = {
            "metrics": {"retrieval_recall_at_5": 0.85},
            "confidence_intervals": {
                "metrics": {
                    "retrieval_recall_at_5": {"mean": 0.85, "ci_low": 0.55, "ci_high": 1.0, "n": 10.0}
                }
            },
        }
        cfg = {
            "metrics": {"retrieval_recall_at_5": {"minimum": 0.6, "direction": "higher_is_better"}},
        }
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "fail")
        failure = next(x for x in out["failures"] if x["metric"] == "retrieval_recall_at_5")
        self.assertEqual(failure["reason"], "below_minimum")
        self.assertEqual(failure["judged_value"], 0.55)
        self.assertEqual(failure["ci_low"], 0.55)
        self.assertEqual(failure["current"], 0.85)
        self.assertTrue(out["use_confidence_intervals"])
        self.assertIn("retrieval_recall_at_5", out["confidence_interval_metrics"])

    def test_gate_uses_ci_high_for_upper_bound_checks(self) -> None:
        # lower_is_better: 点估计 1.8 未超上限, 但 ci_high=2.3 超过 maximum=2.0 → fail
        report = {
            "metrics": {"latency_p95_ms": 1.8},
            "confidence_intervals": {
                "metrics": {"latency_p95_ms": {"mean": 1.8, "ci_low": 1.0, "ci_high": 2.3, "n": 10.0}}
            },
        }
        cfg = {"metrics": {"latency_p95_ms": {"maximum": 2.0, "direction": "lower_is_better"}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "fail")
        failure = out["failures"][0]
        self.assertEqual(failure["reason"], "above_maximum")
        self.assertEqual(failure["judged_value"], 2.3)

    def test_gate_ci_disabled_falls_back_to_point_estimate(self) -> None:
        report = {
            "metrics": {"retrieval_recall_at_5": 0.85},
            "confidence_intervals": {
                "metrics": {
                    "retrieval_recall_at_5": {"mean": 0.85, "ci_low": 0.55, "ci_high": 1.0, "n": 10.0}
                }
            },
        }
        cfg = {
            "use_confidence_intervals": False,
            "metrics": {"retrieval_recall_at_5": {"minimum": 0.6, "direction": "higher_is_better"}},
        }
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "pass")
        self.assertFalse(out["use_confidence_intervals"])
        self.assertEqual(out["confidence_interval_metrics"], [])

    def test_gate_missing_ci_entry_uses_point_estimate(self) -> None:
        # 指标无 CI 条目时回退点估计
        report = {
            "metrics": {"retrieval_recall_at_5": 0.85},
            "confidence_intervals": {"metrics": {}},
        }
        cfg = {"metrics": {"retrieval_recall_at_5": {"minimum": 0.6, "direction": "higher_is_better"}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "pass")

    def test_gate_malformed_ci_entry_uses_point_estimate(self) -> None:
        report = {
            "metrics": {"retrieval_recall_at_5": 0.85},
            "confidence_intervals": {
                "metrics": {"retrieval_recall_at_5": {"mean": 0.85, "ci_low": "bad", "ci_high": None}}
            },
        }
        cfg = {"metrics": {"retrieval_recall_at_5": {"minimum": 0.6, "direction": "higher_is_better"}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "pass")

    def test_gate_ci_pass_when_ci_low_meets_minimum(self) -> None:
        report = {
            "metrics": {"citations_coverage": 0.9},
            "confidence_intervals": {
                "metrics": {"citations_coverage": {"mean": 0.9, "ci_low": 0.75, "ci_high": 1.0, "n": 20.0}}
            },
        }
        cfg = {"metrics": {"citations_coverage": {"minimum": 0.7, "direction": "higher_is_better"}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
