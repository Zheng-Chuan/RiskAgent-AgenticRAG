from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from pathlib import Path

from riskagent_agenticrag.orchestration.nodes import node_validate_and_save


class ContractMilestone3AcceptanceTest(unittest.TestCase):
    def test_validate_does_not_call_appeal_by_default(self) -> None:
        state = {
            "question": "what is frtb",
            "request_id": "r1",
            "run_id": "run1",
            "max_rounds": 1,
            "current_query": "frtb",
            "docs": [],
            "citations": [],
            "decision_log": [],
            "debug": {},
            "trace": {"nodes": [], "events": []},
            "answer": "short answer",
        }
        with patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value={"category": "x", "message": "y"}), patch(
            "riskagent_agenticrag.orchestration.nodes._llm_appeal_failure"
        ) as mock_appeal, patch(
            "riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[]
        ), patch(
            "riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[]
        ), patch(
            "riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/fake.json"
        ):
            out = node_validate_and_save(state)
        mock_appeal.assert_not_called()
        self.assertEqual(out["status"], "failed")
        self.assertFalse(out["debug"]["llm_appeal_enabled"])

    def test_validate_can_enable_appeal_explicitly(self) -> None:
        state = {
            "question": "what is frtb",
            "request_id": "r1",
            "run_id": "run1",
            "max_rounds": 1,
            "current_query": "frtb",
            "docs": [],
            "citations": [],
            "decision_log": [],
            "debug": {},
            "trace": {"nodes": [], "events": []},
            "answer": "short answer",
        }
        old = os.environ.get("RISKAGENT_ENABLE_LLM_APPEAL")
        os.environ["RISKAGENT_ENABLE_LLM_APPEAL"] = "true"
        try:
            with patch("riskagent_agenticrag.orchestration.nodes.validate_response", return_value={"category": "x", "message": "y"}), patch(
                "riskagent_agenticrag.orchestration.nodes._llm_appeal_failure",
                return_value={"is_false_positive": False, "reason": "keep fail", "suggested_fix": None},
            ) as mock_appeal, patch(
                "riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_evidence_set_from_docs", return_value=[]
            ), patch(
                "riskagent_agenticrag.orchestration.nodes.agentic_primitives.build_claims_from_answer", return_value=[]
            ), patch(
                "riskagent_agenticrag.orchestration.nodes.save_artifact", return_value="/tmp/fake.json"
            ):
                out = node_validate_and_save(state)
        finally:
            if old is None:
                os.environ.pop("RISKAGENT_ENABLE_LLM_APPEAL", None)
            else:
                os.environ["RISKAGENT_ENABLE_LLM_APPEAL"] = old
        mock_appeal.assert_called_once()
        self.assertEqual(out["status"], "failed")
        self.assertTrue(out["debug"]["llm_appeal_enabled"])

    def test_committed_report_and_threshold_files_exist(self) -> None:
        root = Path("/Users/zhengchuan/Documents/TECH/Repo/RiskAgent-AgenticRAG")
        self.assertTrue((root / "config" / "eval_thresholds.json").exists())
        self.assertTrue((root / ".artifacts" / "reports" / "rag_eval_baseline_sample.json").exists())
        self.assertTrue((root / ".artifacts" / "reports" / "rag_eval_baseline_sample.md").exists())


if __name__ == "__main__":
    unittest.main()
