from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

from tests.conftest import ensure_src_on_path

ensure_src_on_path()

mod = importlib.import_module("riskagent_agenticrag.evaluation.thresholds")
evaluate_threshold_gate = mod.evaluate_threshold_gate
load_thresholds = mod.load_thresholds


class Week15ThresholdGateTest(unittest.TestCase):
    def test_load_thresholds_json_yaml_superset(self) -> None:
        data = {"metrics": {"a": {"minimum": 0.5}}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "thresholds.yaml"
            p.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_thresholds(str(p))
        self.assertEqual(loaded["metrics"]["a"]["minimum"], 0.5)

    def test_gate_fail_on_absolute_threshold(self) -> None:
        report = {"metrics": {"retrieval_recall_at_5": 0.4}}
        cfg = {"metrics": {"retrieval_recall_at_5": {"minimum": 0.6, "direction": "higher_is_better"}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "fail")
        self.assertTrue(any(x["reason"] == "below_minimum" for x in out["failures"]))

    def test_gate_fail_on_regression(self) -> None:
        report = {"metrics": {"citations_coverage": 0.9}}
        diff = {"citations_coverage": {"regression": True, "delta": -0.1, "current": 0.9, "baseline": 1.0}}
        cfg = {"fail_on_regression": True, "metrics": {}}
        out = evaluate_threshold_gate(report=report, baseline_diff=diff, config=cfg)
        self.assertEqual(out["verdict"], "fail")
        self.assertTrue(any(x["reason"] == "baseline_regression" for x in out["failures"]))

    def test_gate_warning_when_metric_missing(self) -> None:
        report = {"metrics": {}}
        cfg = {"metrics": {"latency_p95_ms": {"maximum": 2000.0}}}
        out = evaluate_threshold_gate(report=report, baseline_diff=None, config=cfg)
        self.assertEqual(out["verdict"], "warning")
        self.assertTrue(any(x["reason"] == "missing_metric" for x in out["warnings"]))


if __name__ == "__main__":
    unittest.main()
