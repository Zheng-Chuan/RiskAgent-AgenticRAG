"""Unit tests for validators/gates.py - evidence / numeric / refusal gates."""

import pytest

from riskagent_agenticrag.validators.gates import (
    _coverage_ratio,
    _extract_numbers,
    _token_overlap,
    evidence_gate,
    numeric_consistency_gate,
    refusal_gate,
    validate_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(eid: str, snippet: str, source: str = "doc.pdf", chunk_id: str = "c1", start_index: int = 0):
    return {
        "evidence_id": eid,
        "source": source,
        "chunk_id": chunk_id,
        "snippet": snippet,
        "start_index": start_index,
    }


def _make_claim(statement: str, evidence_ids: list[str], claim_id: str = "claim-1"):
    return {"claim_id": claim_id, "statement": statement, "evidence_ids": evidence_ids}


# ---------------------------------------------------------------------------
# evidence_gate
# ---------------------------------------------------------------------------

class TestEvidenceGate:

    @pytest.mark.unit
    def test_empty_claims_pass(self):
        result = evidence_gate(claims=[], evidence_set=[])
        assert result is None

    @pytest.mark.unit
    def test_claim_with_valid_evidence_passes(self):
        evidence = _make_evidence("e1", "The total delta exposure is 500 million")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is None

    @pytest.mark.unit
    def test_claim_without_evidence_ids_fails(self):
        evidence = _make_evidence("e1", "snippet text")
        claim = _make_claim("some claim", [])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is not None
        assert result["category"] == "evidence_missing"

    @pytest.mark.unit
    def test_claim_with_nonexistent_evidence_id_fails(self):
        evidence = _make_evidence("e1", "snippet text")
        claim = _make_claim("some claim", ["e999"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is not None
        assert result["category"] == "evidence_not_found"

    @pytest.mark.unit
    def test_claim_not_supported_by_evidence_fails(self):
        evidence = _make_evidence("e1", "Weather today is sunny and warm")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is not None
        assert result["category"] == "evidence_not_supporting"

    @pytest.mark.unit
    def test_partial_support_with_good_overlap_passes(self):
        evidence = _make_evidence("e1", "The total risk delta exposure for desk FX is 500 million USD")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is None

    @pytest.mark.unit
    def test_incomplete_evidence_anchor_fails(self):
        evidence = {"evidence_id": "e1", "source": "", "chunk_id": "", "snippet": "text"}
        claim = _make_claim("some claim", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is not None
        assert result["category"] == "evidence_incomplete"

    @pytest.mark.unit
    def test_numeric_mismatch_in_evidence_fails(self):
        evidence = _make_evidence("e1", "The exposure value is 100.0 for the desk")
        claim = _make_claim("exposure value is 999.0 for the desk", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[evidence])
        assert result is not None
        assert result["category"] == "evidence_numeric_mismatch"


# ---------------------------------------------------------------------------
# numeric_consistency_gate
# ---------------------------------------------------------------------------

class TestNumericConsistencyGate:

    @pytest.mark.unit
    def test_no_numbers_passes(self):
        result = numeric_consistency_gate(
            report="This is a textual answer with no numbers.",
            claims=[],
            tool_traces=[],
            evidence_set=[],
        )
        assert result is None

    @pytest.mark.unit
    def test_numbers_without_tool_traces_and_no_evidence_fails(self):
        result = numeric_consistency_gate(
            report="The exposure is 500.",
            claims=[],
            tool_traces=[],
            evidence_set=[],
        )
        assert result is not None
        assert result["category"] == "numeric_stated_without_evidence"

    @pytest.mark.unit
    def test_numbers_without_tool_traces_but_with_evidence_passes(self):
        evidence = [_make_evidence("e1", "Exposure is 500")]
        result = numeric_consistency_gate(
            report="The exposure is 500.",
            claims=[],
            tool_traces=[],
            evidence_set=evidence,
        )
        assert result is None

    @pytest.mark.unit
    def test_calculated_number_matches_tool_output_passes(self):
        result = numeric_consistency_gate(
            report="计算得出总计 total is 1500.0 for the desk.",
            claims=[{"statement": "计算结果是 1500.0"}],
            tool_traces=[{"tool_output": {"total_delta": 1500.0}}],
            evidence_set=[_make_evidence("e1", "tool data")],
        )
        assert result is None

    @pytest.mark.unit
    def test_calculated_number_mismatch_fails(self):
        result = numeric_consistency_gate(
            report="计算得出 total is 9999.0 for the desk.",
            claims=[{"statement": "计算结果是 9999.0"}],
            tool_traces=[{"tool_output": {"total_delta": 1500.0}}],
            evidence_set=[_make_evidence("e1", "tool data")],
        )
        assert result is not None
        assert result["category"] == "numeric_calculated_mismatch"

    @pytest.mark.unit
    def test_precision_within_tolerance_passes(self):
        """1% relative tolerance - 1500 vs 1505 should pass."""
        result = numeric_consistency_gate(
            report="计算得出 total is 1505.0 for the desk.",
            claims=[],
            tool_traces=[{"tool_output": {"total_delta": 1500.0}}],
            evidence_set=[_make_evidence("e1", "data")],
        )
        assert result is None

    @pytest.mark.unit
    def test_no_tool_numbers_passes(self):
        """If tool traces exist but have no numeric output, pass."""
        result = numeric_consistency_gate(
            report="计算得出 total is 100.",
            claims=[],
            tool_traces=[{"tool_output": {"status": "ok"}}],
            evidence_set=[_make_evidence("e1", "data")],
        )
        assert result is None


# ---------------------------------------------------------------------------
# refusal_gate
# ---------------------------------------------------------------------------

class TestRefusalGate:

    @pytest.mark.unit
    def test_docs_and_evidence_present_passes(self):
        result = refusal_gate(
            docs=["doc1"],
            evidence_set=[_make_evidence("e1", "text")],
            report="Here is the analysis...",
        )
        assert result is None

    @pytest.mark.unit
    def test_no_docs_with_proper_refusal_passes(self):
        report = "很抱歉，无法回答您的问题，检索文档不足。建议您可以补充相关的风险数据文档。"
        result = refusal_gate(docs=[], evidence_set=[], report=report)
        assert result is None

    @pytest.mark.unit
    def test_no_docs_without_refusal_fails(self):
        report = "The desk exposure is 500 million which means the limit is breached."
        result = refusal_gate(docs=[], evidence_set=[], report=report)
        assert result is not None
        assert result["category"] == "retrieval_empty"

    @pytest.mark.unit
    def test_no_evidence_without_refusal_fails(self):
        report = "The desk exposure is 500 million which means the limit is breached."
        result = refusal_gate(docs=["doc1"], evidence_set=[], report=report)
        assert result is not None
        assert result["category"] == "no_evidence"

    @pytest.mark.unit
    def test_refusal_without_next_actions_fails(self):
        report = "很抱歉，我不知道这个问题的答案，检索文档不足以回答。"
        result = refusal_gate(docs=[], evidence_set=[], report=report)
        assert result is not None
        assert result["category"] == "refusal_unclear"

    @pytest.mark.unit
    def test_short_report_when_empty_docs_fails(self):
        result = refusal_gate(docs=[], evidence_set=[], report="No.")
        assert result is not None
        assert result["category"] == "refusal_incomplete"


# ---------------------------------------------------------------------------
# validate_response (orchestration)
# ---------------------------------------------------------------------------

class TestValidateResponse:

    @pytest.mark.unit
    def test_all_gates_pass(self):
        evidence = _make_evidence("e1", "The total delta exposure for desk FX is 500 million")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = validate_response(
            report="The total delta exposure is 500 million.",
            claims=[claim],
            evidence_set=[evidence],
            tool_traces=[],
            docs=["doc1"],
        )
        assert result is None

    @pytest.mark.unit
    def test_refusal_gate_fails_first(self):
        """Refusal gate runs first; if docs empty, it should fail before evidence gate."""
        claim = _make_claim("some claim", [])
        result = validate_response(
            report="The answer is 42.",
            claims=[claim],
            evidence_set=[],
            tool_traces=[],
            docs=[],
        )
        assert result is not None
        assert result["category"] in ("retrieval_empty", "refusal_incomplete")

    @pytest.mark.unit
    def test_numeric_gate_disabled(self):
        evidence = _make_evidence("e1", "The total delta exposure for desk FX is 500 million")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = validate_response(
            report="计算得出 total is 9999.0 for the desk.",
            claims=[claim],
            evidence_set=[evidence],
            tool_traces=[{"tool_output": {"value": 1500.0}}],
            docs=["doc1"],
            require_numeric_backing=False,
        )
        assert result is None

    @pytest.mark.unit
    def test_compound_failure_returns_first(self):
        """When multiple gates would fail, only the first failure is returned."""
        result = validate_response(
            report="Short",
            claims=[_make_claim("claim", [])],
            evidence_set=[],
            tool_traces=[],
            docs=[],
        )
        assert result is not None
        # refusal_gate fires first since docs and evidence are empty
        assert "refusal" in result["category"] or "retrieval" in result["category"]


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:

    @pytest.mark.unit
    def test_extract_numbers_basic(self):
        nums = _extract_numbers("The value is 42.5 and 100")
        assert 42.5 in nums
        assert 100.0 in nums

    @pytest.mark.unit
    def test_extract_numbers_percentage(self):
        nums = _extract_numbers("Growth rate is 15%")
        assert abs(nums[0] - 0.15) < 1e-9

    @pytest.mark.unit
    def test_extract_numbers_ignores_chunk_refs(self):
        nums = _extract_numbers("[source=doc chunk_id=chunk_42] value is 100")
        assert 42.0 not in nums
        assert 100.0 in nums

    @pytest.mark.unit
    def test_token_overlap(self):
        overlap = _token_overlap("hello world test", "world test foo")
        assert overlap == 2

    @pytest.mark.unit
    def test_coverage_ratio(self):
        ratio = _coverage_ratio("hello world", "hello world foo bar")
        assert ratio >= 0.9
