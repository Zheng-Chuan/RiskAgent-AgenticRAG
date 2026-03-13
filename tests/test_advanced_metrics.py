from __future__ import annotations

import importlib
import unittest



metrics_mod = importlib.import_module("riskagent_agenticrag.evaluation.advanced_metrics")
compute_retrieval_metrics = metrics_mod.compute_retrieval_metrics
compute_gate_metrics = metrics_mod.compute_gate_metrics
compute_reliability_cost_metrics = metrics_mod.compute_reliability_cost_metrics
compare_reports = importlib.import_module("riskagent_agenticrag.evaluation.reporting").compare_reports


class Week14AdvancedMetricsTest(unittest.TestCase):
    def test_retrieval_metrics(self) -> None:
        samples = [
            {
                "citations": [{"source": "corpus/a.md", "chunk_id": "a1"}],
                "retrieved_docs": [
                    {"source": "corpus/a.md", "chunk_id": "a1", "dense_rank": 1, "rrf_score": 0.2, "rerank_score": 0.9},
                    {"source": "corpus/b.md", "chunk_id": "b1", "sparse_rank": 1, "rrf_score": 0.9, "rerank_score": 0.1},
                ],
            },
            {
                "citations": [{"source": "corpus/c.md", "chunk_id": "c1"}],
                "retrieved_docs": [
                    {"source": "corpus/x.md", "chunk_id": "x1", "dense_rank": 1},
                    {"source": "corpus/c.md", "chunk_id": "c1", "sparse_rank": 1},
                ],
            },
        ]
        out = compute_retrieval_metrics(samples=samples, ks=[1, 2]).metrics
        self.assertIn("retrieval_mrr", out)
        self.assertIn("retrieval_recall_at_1", out)
        self.assertIn("retrieval_recall_at_2", out)
        self.assertGreaterEqual(float(out["retrieval_recall_at_2"]), float(out["retrieval_recall_at_1"]))

    def test_gate_and_reliability_metrics(self) -> None:
        samples = [
            {"status": "ok", "failure_reason": None, "answer": "a", "valid_citation_count": 1, "latency_ms": 120.0},
            {
                "status": "failed",
                "failure_reason": {"code": "E_TIMEOUT"},
                "answer": "",
                "valid_citation_count": 0,
                "latency_ms": 330.0,
                "node_latencies": {"retrieve_and_critique": 200.0},
            },
        ]
        gate = compute_gate_metrics(samples=samples)
        self.assertIn("gate_block_rate", gate.metrics)
        self.assertIn("failure_reason_distribution", gate.distributions)
        rc = compute_reliability_cost_metrics(samples=samples, include_latency=True, include_cost=True)
        self.assertIn("reliability_success_rate", rc.metrics)
        self.assertIn("latency_p95_ms", rc.metrics)
        self.assertIn("cost_estimated_usd", rc.metrics)

    def test_compare_reports_extended_metrics(self) -> None:
        baseline = {
            "metrics": {
                "retrieval_recall_at_5": 0.9,
                "reliability_error_rate": 0.1,
                "hallucination_rate_in_citations": 0.3,
            }
        }
        current = {
            "metrics": {
                "retrieval_recall_at_5": 0.8,
                "reliability_error_rate": 0.2,
                "hallucination_rate_in_citations": 0.4,
            }
        }
        diff = compare_reports(
            current_report=current,
            baseline_report=baseline,
            tolerance=0.01,
            minimum=0.0,
            hallucination_maximum=0.35,
        )
        self.assertTrue(diff["retrieval_recall_at_5"]["regression"])
        self.assertTrue(diff["reliability_error_rate"]["regression"])
        self.assertTrue(diff["hallucination_rate_in_citations"]["regression"])


if __name__ == "__main__":
    unittest.main()
