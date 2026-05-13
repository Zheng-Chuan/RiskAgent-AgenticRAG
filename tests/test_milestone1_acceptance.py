from __future__ import annotations

import unittest


class ContractMilestone1AcceptanceTest(unittest.TestCase):
    def test_langgraph_mainline_is_pure_rag(self) -> None:
        from riskagent_agenticrag.orchestration.langgraph_runner import visualize_graph_mermaid

        mermaid = visualize_graph_mermaid()

        self.assertIn("rewrite", mermaid)
        self.assertIn("retrieve", mermaid)
        self.assertIn("synthesize", mermaid)
        self.assertIn("validate", mermaid)
        self.assertNotIn("decide_tool", mermaid)
        self.assertNotIn("call_tool", mermaid)

    def test_structured_response_accepts_pure_rag_payload(self) -> None:
        from riskagent_agenticrag.contracts.structured import parse_structured_response

        payload = parse_structured_response(
            {
                "request_id": "r1",
                "report": "answer",
                "evidence_set": [],
                "claims": [],
                "decision_log": [],
                "status": "ok",
                "failure_reason": None,
            }
        )

        self.assertEqual(payload.request_id, "r1")
        self.assertEqual(payload.report, "answer")
        self.assertEqual(payload.tool_traces, [])
        self.assertEqual(payload.breaches, [])
