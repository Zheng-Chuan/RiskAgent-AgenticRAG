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

    @pytest.mark.unit
    def test_coverage_ratio_empty_statement(self):
        """空 statement 应返回 0.0."""
        assert _coverage_ratio("", "evidence text") == 0.0

    @pytest.mark.unit
    def test_coverage_ratio_empty_evidence(self):
        """空 evidence 应返回 0.0."""
        assert _coverage_ratio("some statement", "") == 0.0

    @pytest.mark.unit
    def test_collect_numbers_none(self):
        """None 输入应返回空列表."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        assert _collect_numbers(None) == []

    @pytest.mark.unit
    def test_collect_numbers_int(self):
        """int 输入应返回单元素列表."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        assert _collect_numbers(42) == [42.0]

    @pytest.mark.unit
    def test_collect_numbers_float(self):
        """float 输入应返回单元素列表."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        assert _collect_numbers(3.14) == [3.14]

    @pytest.mark.unit
    def test_collect_numbers_string(self):
        """string 输入应调用 _extract_numbers."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        assert _collect_numbers("value 100") == [100.0]

    @pytest.mark.unit
    def test_collect_numbers_dict(self):
        """dict 输入应递归收集所有值中的数字."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        result = _collect_numbers({"a": "x 50", "b": 10, "c": [1, 2]})
        assert 50.0 in result
        assert 10.0 in result
        assert 1.0 in result
        assert 2.0 in result

    @pytest.mark.unit
    def test_collect_numbers_list(self):
        """list 输入应递归收集所有元素中的数字."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        result = _collect_numbers(["x 5", 10, {"v": 20}])
        assert 5.0 in result
        assert 10.0 in result
        assert 20.0 in result

    @pytest.mark.unit
    def test_collect_numbers_other_type(self):
        """其它类型应返回空列表."""
        from riskagent_agenticrag.validators.gates import _collect_numbers
        assert _collect_numbers(object()) == []


# ---------------------------------------------------------------------------
# _evidence_anchor_complete 分支测试
# ---------------------------------------------------------------------------


class TestEvidenceAnchorComplete:

    @pytest.mark.unit
    def test_missing_source_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"chunk_id": "c1", "snippet": "text"}) is False

    @pytest.mark.unit
    def test_missing_chunk_id_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "snippet": "text"}) is False

    @pytest.mark.unit
    def test_missing_snippet_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1"}) is False

    @pytest.mark.unit
    def test_start_index_negative_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "start_index": -1}) is False

    @pytest.mark.unit
    def test_start_index_valid_returns_true(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "start_index": 5}) is True

    @pytest.mark.unit
    def test_start_line_negative_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "start_line": -1}) is False

    @pytest.mark.unit
    def test_start_line_valid_returns_true(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "start_line": 10}) is True

    @pytest.mark.unit
    def test_page_negative_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "page": -1}) is False

    @pytest.mark.unit
    def test_page_valid_returns_true(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "page": 1}) is True

    @pytest.mark.unit
    def test_no_anchor_fields_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t"}) is False

    @pytest.mark.unit
    def test_invalid_start_index_returns_false(self):
        from riskagent_agenticrag.validators.gates import _evidence_anchor_complete
        assert _evidence_anchor_complete({"source": "s", "chunk_id": "c1", "snippet": "t", "start_index": "abc"}) is False


# ---------------------------------------------------------------------------
# _numbers_supported 分支测试
# ---------------------------------------------------------------------------


class TestNumbersSupported:

    @pytest.mark.unit
    def test_no_numbers_in_statement_passes(self):
        from riskagent_agenticrag.validators.gates import _numbers_supported
        assert _numbers_supported("no numbers here", "evidence text") is True

    @pytest.mark.unit
    def test_numbers_in_statement_no_evidence_numbers_fails(self):
        from riskagent_agenticrag.validators.gates import _numbers_supported
        assert _numbers_supported("value 100", "no numbers") is False

    @pytest.mark.unit
    def test_exact_match_passes(self):
        from riskagent_agenticrag.validators.gates import _numbers_supported
        assert _numbers_supported("value 100", "the value 100") is True

    @pytest.mark.unit
    def test_relative_match_passes(self):
        from riskagent_agenticrag.validators.gates import _numbers_supported
        # 100 vs 100.5, 0.5% difference <= 1%
        assert _numbers_supported("value 100", "the value 100.5") is True

    @pytest.mark.unit
    def test_mismatch_fails(self):
        from riskagent_agenticrag.validators.gates import _numbers_supported
        assert _numbers_supported("value 100", "the value 200") is False


# ---------------------------------------------------------------------------
# _classify_number_context 分支测试
# ---------------------------------------------------------------------------


class TestClassifyNumberContext:

    @pytest.mark.unit
    def test_calculated_keyword(self):
        from riskagent_agenticrag.validators.gates import _classify_number_context
        result = _classify_number_context("the total is calculated as 500", 500.0)
        assert result == "calculated"

    @pytest.mark.unit
    def test_stated_with_citation(self):
        from riskagent_agenticrag.validators.gates import _classify_number_context
        result = _classify_number_context("the value [source=doc] is 500", 500.0)
        assert result == "stated"

    @pytest.mark.unit
    def test_unknown_when_number_not_found(self):
        from riskagent_agenticrag.validators.gates import _classify_number_context
        result = _classify_number_context("no such number here", 999.0)
        assert result == "unknown"

    @pytest.mark.unit
    def test_default_stated(self):
        from riskagent_agenticrag.validators.gates import _classify_number_context
        result = _classify_number_context("the value 500 is reported", 500.0)
        assert result == "stated"

    @pytest.mark.unit
    def test_float_number_match(self):
        from riskagent_agenticrag.validators.gates import _classify_number_context
        result = _classify_number_context("total equals 3.14", 3.14)
        assert result == "calculated"


# ---------------------------------------------------------------------------
# evidence_gate: 非字典 evidence 处理
# ---------------------------------------------------------------------------


class TestEvidenceGateEdgeCases:

    @pytest.mark.unit
    def test_evidence_without_id_skipped(self):
        """无 evidence_id 的 evidence 应在 evidence_text_by_id 构建时被跳过."""
        # 该 evidence 有完整锚点但无 evidence_id, 不影响有 id 的 evidence 校验
        no_id_evidence = {
            "source": "s", "chunk_id": "c2", "snippet": "text", "start_index": 0,
        }
        evidence = _make_evidence("e1", "The total delta exposure is 500 million")
        claim = _make_claim("total delta exposure is 500 million", ["e1"])
        result = evidence_gate(claims=[claim], evidence_set=[no_id_evidence, evidence])
        assert result is None


# ---------------------------------------------------------------------------
# numeric_consistency_gate: 分类数字路径
# ---------------------------------------------------------------------------


class TestNumericConsistencyClassification:

    @pytest.mark.unit
    def test_stated_numbers_without_tools_passes(self):
        """有 tool_traces 但数字是陈述型 (非计算型) 时应通过."""
        evidence = _make_evidence("e1", "The value is 500 million as stated")
        claim = _make_claim("value is 500 million", ["e1"])
        result = numeric_consistency_gate(
            report="The value is 500 million as stated.",
            claims=[claim],
            tool_traces=[{"tool_output": {"value": 999}}],
            evidence_set=[evidence],
        )
        assert result is None

    @pytest.mark.unit
    def test_calculated_numbers_match_tool_output(self):
        """计算型数字与 tool 输出匹配时应通过."""
        result = numeric_consistency_gate(
            report="the calculated total equals 100",
            claims=[],
            tool_traces=[{"tool_output": {"value": 100}}],
            evidence_set=[],
        )
        assert result is None

    @pytest.mark.unit
    def test_calculated_numbers_with_no_tool_numbers_passes(self):
        """计算型数字但 tool 无数字时应通过 (tool_numbers 为空)."""
        result = numeric_consistency_gate(
            report="the calculated total equals 100",
            claims=[],
            tool_traces=[{"tool_output": "no numbers here"}],
            evidence_set=[],
        )
        assert result is None

    @pytest.mark.unit
    def test_calculated_numbers_mismatch_fails(self):
        """计算型数字与 tool 输出不匹配时应失败."""
        result = numeric_consistency_gate(
            report="the calculated total equals 100",
            claims=[],
            tool_traces=[{"tool_output": {"value": 200}}],
            evidence_set=[],
        )
        assert result is not None
        assert result["category"] == "numeric_calculated_mismatch"
