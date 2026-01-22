from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.conftest import ensure_src_on_path


class FailureTaxonomyCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def test_failure_categories_have_use_cases(self) -> None:
        from riskagent_rag.agents.data_agent import run_data_agent
        from riskagent_rag.contracts.structured import StructuredRequest, try_parse_structured_response
        from riskagent_rag.validators.gates import evidence_gate, numeric_consistency_gate, refusal_gate

        # evidence_missing
        f = evidence_gate(claims=[{"claim_id": "c1", "statement": "x", "evidence_ids": []}], evidence_set=[{"evidence_id": "ev_0", "chunk_id": "c"}])
        self.assertEqual(f["category"], "evidence_missing")

        # evidence_not_found
        f = evidence_gate(
            claims=[{"claim_id": "c1", "statement": "x", "evidence_ids": ["ev_999"]}],
            evidence_set=[{"evidence_id": "ev_0", "chunk_id": "c"}],
        )
        self.assertEqual(f["category"], "evidence_not_found")

        # evidence_incomplete
        f = evidence_gate(
            claims=[{"claim_id": "c1", "statement": "x", "evidence_ids": ["ev_0"]}],
            evidence_set=[{"evidence_id": "ev_0", "chunk_id": ""}],
        )
        self.assertEqual(f["category"], "evidence_incomplete")

        # evidence_not_supporting
        f = evidence_gate(
            claims=[{"claim_id": "c1", "statement": "totally unrelated", "evidence_ids": ["ev_0"]}],
            evidence_set=[{"evidence_id": "ev_0", "chunk_id": "chunk_0", "snippet": "abc def"}],
        )
        self.assertEqual(f["category"], "evidence_not_supporting")

        # numeric_inconsistent
        f = numeric_consistency_gate(
            report="Delta is 1000.",
            claims=[{"statement": "Delta is 1000"}],
            tool_traces=[{"tool_name": "t", "tool_output": {"delta": 900}}],
        )
        self.assertEqual(f["category"], "numeric_inconsistent")

        # refusal_incomplete
        f = refusal_gate(docs=[], evidence_set=[], report="too short")
        self.assertEqual(f["category"], "refusal_incomplete")

        # refusal_unclear (has refusal but no next actions)
        f = refusal_gate(docs=[], evidence_set=[], report="I do not know the answer.")
        self.assertEqual(f["category"], "refusal_unclear")

        # retrieval_empty (no refusal at all)
        f = refusal_gate(docs=[], evidence_set=[], report="This is an answer without evidence and without refusal.")
        self.assertEqual(f["category"], "retrieval_empty")

        # no_evidence (docs exist but evidence missing and no refusal)
        f = refusal_gate(docs=[{"page_content": "x"}], evidence_set=[], report="This is an answer without evidence and without refusal.")
        self.assertEqual(f["category"], "no_evidence")

        # tool_error
        req = StructuredRequest(request_id="r1", query="q", as_of="2026-01-01", desk="D1", abs_delta_limit=1.0)
        with patch("riskagent_rag.agents.data_agent.monitor_desk_exposure", side_effect=RuntimeError("boom")):
            _out, _trace, failure = run_data_agent(req)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.category, "tool_error")

        # parse_error
        _parsed, failure = try_parse_structured_response({"not": "a structured response"})
        self.assertIsNotNone(failure)
        self.assertEqual(failure.category, "parse_error")

