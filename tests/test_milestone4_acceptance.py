from __future__ import annotations

import unittest
from pathlib import Path

from riskagent_agenticrag.evaluation.thresholds import load_thresholds


class ContractMilestone4AcceptanceTest(unittest.TestCase):
    def test_environment_lock_files_exist(self) -> None:
        root = Path("/Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG")
        self.assertTrue((root / "environment.yml").exists())
        self.assertTrue((root / "requirements-lock.txt").exists())

    def test_release_acceptance_scripts_exist(self) -> None:
        root = Path("/Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG")
        offline_script = (root / "scripts" / "run_offline_regression.sh").read_text(encoding="utf-8")
        release_script = (root / "scripts" / "release_acceptance.sh").read_text(encoding="utf-8")
        self.assertIn("tests/test_milestone1_acceptance.py", offline_script)
        self.assertIn("scripts/run_offline_regression.sh", release_script)

    def test_threshold_config_contains_release_metrics(self) -> None:
        root = Path("/Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG")
        cfg = load_thresholds(root / "config" / "eval_thresholds.json")
        self.assertIn("metrics", cfg)
        metrics = cfg["metrics"]
        self.assertIn("citation_coverage", metrics)
        self.assertIn("faithfulness", metrics)
        self.assertIn("answer_relevancy", metrics)
        self.assertIn("retrieval_recall_at_5", metrics)


if __name__ == "__main__":
    unittest.main()
