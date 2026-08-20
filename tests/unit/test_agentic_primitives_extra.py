"""Agentic primitives 补充测试.

覆盖 agentic_primitives.py 中未覆盖的纯函数和 LLM 交互函数:
try_parse_json / revise_query / synthesize_answer / attach_citations /
build_evidence_set / _extract_chunk_ids / _split_claim_statements.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from riskagent_agenticrag.rag.agentic_primitives import (
    _extract_chunk_ids_from_text,
    _paragraph_tokens,
    _split_claim_statements,
    attach_citations_to_each_paragraph,
    build_evidence_set_from_docs,
    critique_retrieval,
    rewrite_query,
    revise_query,
    synthesize_answer,
    synthesize_answer_from_model_knowledge,
    try_parse_json,
)


# ---------------------------------------------------------------------------
# try_parse_json
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTryParseJson:
    """JSON 容错解析测试."""

    def test_valid_json(self):
        assert try_parse_json('{"key": "value"}') == {"key": "value"}

    def test_empty_string_returns_none(self):
        assert try_parse_json("") is None
        assert try_parse_json(None) is None
        assert try_parse_json("   ") is None

    def test_json_with_surrounding_text(self):
        """应从文本中提取 JSON 片段."""
        text = 'Here is the result: {"sufficient": true, "reason": "ok"} done.'
        result = try_parse_json(text)
        assert result == {"sufficient": True, "reason": "ok"}

    def test_no_braces_returns_none(self):
        """无大括号时返回 None."""
        assert try_parse_json("just plain text") is None

    def test_invalid_json_in_braces_returns_none(self):
        """大括号内非 JSON 时返回 None."""
        assert try_parse_json("{not valid json}") is None


# ---------------------------------------------------------------------------
# revise_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReviseQuery:
    """查询改写测试."""

    def test_returns_revised_query_from_llm(self, llm_mock):
        """LLM 返回新 query 时应使用它."""
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", return_value={"query": "revised query"}):
            result = revise_query("original question", "previous query")
        assert result == "revised query"

    def test_llm_failure_falls_back_to_previous(self, llm_mock):
        """LLM 异常时回退到 previous_query."""
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=RuntimeError("boom")):
            result = revise_query("original", "previous query")
        assert result == "previous query"

    def test_empty_llm_query_falls_back(self, llm_mock):
        """LLM 返回空 query 时回退."""
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", return_value={"query": ""}):
            result = revise_query("q", "prev")
        assert result == "prev"

    def test_empty_previous_falls_back_to_question(self, llm_mock):
        """previous_query 为空时用 question 作为回退."""
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=RuntimeError("boom")):
            result = revise_query("the question", "")
        assert result == "the question"


# ---------------------------------------------------------------------------
# synthesize_answer / synthesize_answer_from_model_knowledge
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSynthesizeAnswer:
    """答案合成测试."""

    def test_empty_docs_calls_refusal_report(self, llm_mock):
        """空 docs 应调用 build_refusal_report (返回拒答文本)."""
        result = synthesize_answer(question="What is FRTB?", docs=[])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_docs_with_empty_content_calls_refusal(self, llm_mock):
        """docs 内容全空时应调用拒答."""
        docs = [Document(page_content="   ", metadata={})]
        result = synthesize_answer(question="q", docs=docs)
        assert isinstance(result, str)

    def test_docs_with_content_calls_generate(self, llm_mock):
        """有内容的 docs 应调用 generate_answer."""
        docs = [Document(page_content="FRTB is a framework.", metadata={"source": "s"})]
        result = synthesize_answer(question="What is FRTB?", docs=docs)
        assert isinstance(result, str)


@pytest.mark.unit
class TestSynthesizeFromModelKnowledge:
    """模型知识直答测试."""

    def test_calls_llm_with_prompt(self, llm_mock):
        """应调用 LLM 生成回答."""
        result = synthesize_answer_from_model_knowledge("What is delta risk?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_question_still_calls(self, llm_mock):
        """空问题也应能调用 (不崩溃)."""
        result = synthesize_answer_from_model_knowledge("")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# attach_citations_to_each_paragraph
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAttachCitations:
    """段落级 citation 匹配测试."""

    def test_empty_answer_returned_as_is(self):
        """空答案原样返回."""
        assert attach_citations_to_each_paragraph("", [{"source": "s"}]) == ""

    def test_no_citations_returned_as_is(self):
        """无 citations 原样返回."""
        answer = "Some answer text."
        assert attach_citations_to_each_paragraph(answer, []) == answer

    def test_matching_citations_appended(self):
        """匹配的 citation 应附加到段落."""
        answer = "Delta risk measures sensitivity to underlying factors."
        citations = [
            {"source": "doc1", "chunk_id": "c1", "snippet": "delta risk sensitivity"},
            {"source": "doc2", "chunk_id": "c2", "snippet": "vega risk unrelated"},
        ]
        result = attach_citations_to_each_paragraph(answer, citations)
        assert "Citations:" in result
        assert "doc1" in result

    def test_no_matching_citations_not_appended(self):
        """无匹配时不应附加 citation."""
        answer = "General text about nothing specific."
        citations = [{"source": "d", "chunk_id": "c", "snippet": "completely different content xyz"}]
        result = attach_citations_to_each_paragraph(answer, citations)
        assert "Citations:" not in result

    def test_multiple_paragraphs(self):
        """多段落应分别匹配."""
        answer = "Delta risk is important.\n\nVega risk is also relevant."
        citations = [
            {"source": "d1", "chunk_id": "c1", "snippet": "delta risk"},
            {"source": "d2", "chunk_id": "c2", "snippet": "vega risk"},
        ]
        result = attach_citations_to_each_paragraph(answer, citations)
        assert "d1" in result
        assert "d2" in result


# ---------------------------------------------------------------------------
# build_evidence_set_from_docs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildEvidenceSet:
    """从 docs 构建 evidence_set 测试."""

    def test_empty_docs_returns_empty(self):
        assert build_evidence_set_from_docs([], include_text=False) == []

    def test_basic_evidence_fields(self):
        """应包含 evidence_id / source / chunk_id / start_index / snippet."""
        docs = [Document(page_content="content here", metadata={"source": "s", "chunk_id": "c1"})]
        result = build_evidence_set_from_docs(docs, include_text=False)
        assert len(result) == 1
        assert result[0]["evidence_id"] == "ev_0"
        assert result[0]["source"] == "s"
        assert result[0]["chunk_id"] == "c1"
        assert "snippet" in result[0]
        assert "text" not in result[0]

    def test_include_text_adds_text_field(self):
        """include_text=True 时应包含 text 字段."""
        docs = [Document(page_content="full content", metadata={"source": "s"})]
        result = build_evidence_set_from_docs(docs, include_text=True)
        assert "text" in result[0]

    def test_optional_metadata_fields(self):
        """有 tool_name / evidence_kind / numeric_payload / section_path 时应包含."""
        docs = [
            Document(
                page_content="c",
                metadata={
                    "source": "s", "chunk_id": "c", "tool_name": "calc",
                    "evidence_kind": "numeric", "numeric_payload": {"value": 42},
                    "section_path": "Risk/Delta", "start_line": 1, "end_line": 5, "page": 2,
                },
            )
        ]
        result = build_evidence_set_from_docs(docs, include_text=False)
        assert result[0]["tool_name"] == "calc"
        assert result[0]["evidence_kind"] == "numeric"
        assert result[0]["numeric_payload"] == {"value": 42}
        assert result[0]["section_path"] == "Risk/Delta"
        assert result[0]["start_line"] == 1
        assert result[0]["end_line"] == 5
        assert result[0]["page"] == 2

    def test_invalid_start_index_defaults_to_zero(self):
        """start_index 非法时应默认为 0."""
        docs = [Document(page_content="c", metadata={"source": "s", "start_index": "abc"})]
        result = build_evidence_set_from_docs(docs, include_text=False)
        assert result[0]["start_index"] == 0

    def test_expanded_text_used_for_snippet(self):
        """有 expanded_text 时 snippet 应优先使用它."""
        docs = [Document(page_content="original", metadata={"source": "s", "expanded_text": "expanded"})]
        result = build_evidence_set_from_docs(docs, include_text=False)
        assert result[0]["snippet"] == "expanded"

    def test_multiple_docs_incrementing_ids(self):
        """多 docs 应有递增的 evidence_id."""
        docs = [Document(page_content="a", metadata={}), Document(page_content="b", metadata={})]
        result = build_evidence_set_from_docs(docs, include_text=False)
        assert result[0]["evidence_id"] == "ev_0"
        assert result[1]["evidence_id"] == "ev_1"


# ---------------------------------------------------------------------------
# _extract_chunk_ids_from_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractChunkIds:
    """从文本提取 chunk_id 测试."""

    def test_extracts_single_id(self):
        text = "Citations: [source=doc.md chunk_id=c123]"
        assert _extract_chunk_ids_from_text(text) == ["c123"]

    def test_extracts_multiple_unique(self):
        text = "[source=a chunk_id=c1] [source=b chunk_id=c2] [source=c chunk_id=c1]"
        result = _extract_chunk_ids_from_text(text)
        assert result == ["c1", "c2"]  # 去重

    def test_empty_text_returns_empty(self):
        assert _extract_chunk_ids_from_text("") == []
        assert _extract_chunk_ids_from_text(None) == []

    def test_no_chunk_ids_returns_empty(self):
        assert _extract_chunk_ids_from_text("no citations here") == []


# ---------------------------------------------------------------------------
# _split_claim_statements
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSplitClaimStatements:
    """claim 语句切分测试."""

    def test_multiple_lines(self):
        """多行应切分为多个 claim."""
        block = "First claim here.\nSecond claim here.\nThird claim here."
        result = _split_claim_statements(block)
        assert len(result) == 3
        assert "First" in result[0]
        assert "Second" in result[1]

    def test_skips_citations_line(self):
        """以 'Citations:' 开头的行应跳过."""
        block = "A claim.\nCitations: [source=x chunk_id=c1]"
        result = _split_claim_statements(block)
        assert len(result) == 1
        assert "A claim" in result[0]

    def test_strips_bullet_markers(self):
        """应移除列表标记 (- 或 *)."""
        block = "- First item\n* Second item"
        result = _split_claim_statements(block)
        assert "- First" not in result[0]
        assert "First item" in result[0]

    def test_empty_block_returns_empty(self):
        """空块返回空列表."""
        assert _split_claim_statements("") == []
        assert _split_claim_statements(None) == []
        assert _split_claim_statements("  \n  ") == []

    def test_single_block_no_lines(self):
        """无换行的单块文本应返回单 claim."""
        result = _split_claim_statements("just one claim")
        assert result == ["just one claim"]
