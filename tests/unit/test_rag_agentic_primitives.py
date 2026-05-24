"""Unit tests for RAG agentic primitives."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# rewrite_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRewriteQuery:
    """Tests for rewrite_query function."""

    def test_prompt_construction_includes_question(self, llm_mock):
        """rewrite_query should incorporate the user question into the prompt."""
        from riskagent_agenticrag.rag.agentic_primitives import rewrite_query

        result = rewrite_query("What is FRTB delta risk?")
        # The mock returns {"query": "rewritten test query"}
        assert result == "rewritten test query"

    def test_json_parse_extracts_query_field(self):
        """rewrite_query should extract the 'query' field from JSON response."""
        from riskagent_agenticrag.rag.agentic_primitives import rewrite_query

        fake_response = {"query": "FRTB delta risk capital requirement"}
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            return_value=fake_response,
        ):
            result = rewrite_query("Explain delta risk in FRTB")
            assert result == "FRTB delta risk capital requirement"

    def test_fallback_returns_original_on_empty_query(self):
        """If LLM returns empty query field, fallback to original question."""
        from riskagent_agenticrag.rag.agentic_primitives import rewrite_query

        fake_response = {"query": ""}
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            return_value=fake_response,
        ):
            result = rewrite_query("What is CVA?")
            assert result == "What is CVA?"

    def test_fallback_returns_original_on_missing_key(self):
        """If LLM returns dict without 'query', fallback to original."""
        from riskagent_agenticrag.rag.agentic_primitives import rewrite_query

        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            return_value={},
        ):
            result = rewrite_query("FRTB overview")
            assert result == "FRTB overview"


# ---------------------------------------------------------------------------
# critique_retrieval
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCritiqueRetrieval:
    """Tests for critique_retrieval function."""

    def test_sufficient_decision(self):
        """When LLM deems context sufficient, returns (True, ...)."""
        from riskagent_agenticrag.rag.agentic_primitives import critique_retrieval

        docs = [Document(page_content="FRTB capital requirement details")]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            return_value={"sufficient": True, "improved_query": "", "reason": "context covers the question"},
        ):
            sufficient, improved_query, reason = critique_retrieval("What is FRTB?", docs)
            assert sufficient is True
            assert reason == "context covers the question"

    def test_insufficient_decision_with_improved_query(self):
        """When insufficient, returns improved_query for retry."""
        from riskagent_agenticrag.rag.agentic_primitives import critique_retrieval

        docs = [Document(page_content="Unrelated text about weather.")]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            return_value={
                "sufficient": False,
                "improved_query": "FRTB standardized approach capital charge",
                "reason": "context does not mention FRTB",
            },
        ):
            sufficient, improved_query, reason = critique_retrieval("FRTB capital?", docs)
            assert sufficient is False
            assert improved_query == "FRTB standardized approach capital charge"
            assert "FRTB" in reason

    def test_empty_docs_returns_false(self):
        """Empty docs list should immediately return insufficient."""
        from riskagent_agenticrag.rag.agentic_primitives import critique_retrieval

        sufficient, improved_query, reason = critique_retrieval("Test question?", [])
        assert sufficient is False
        assert "empty" in reason


# ---------------------------------------------------------------------------
# synthesize_answer
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSynthesizeAnswer:
    """Tests for synthesize_answer function."""

    def test_generates_answer_with_docs(self):
        """synthesize_answer delegates to generate_answer when docs present."""
        from riskagent_agenticrag.rag.agentic_primitives import synthesize_answer

        docs = [Document(page_content="FRTB is a Basel regulation.")]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.generate_answer",
            return_value="FRTB is the Fundamental Review of the Trading Book.",
        ):
            result = synthesize_answer(question="What is FRTB?", docs=docs)
            assert "FRTB" in result

    def test_refusal_on_empty_docs(self):
        """synthesize_answer returns refusal report when no docs."""
        from riskagent_agenticrag.rag.agentic_primitives import synthesize_answer

        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.build_refusal_report",
            return_value="No evidence found.",
        ):
            result = synthesize_answer(question="What is XYZ?", docs=[])
            assert "No evidence" in result

    def test_refusal_on_empty_content_docs(self):
        """Docs with only blank content trigger refusal."""
        from riskagent_agenticrag.rag.agentic_primitives import synthesize_answer

        docs = [Document(page_content="", metadata={})]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.build_refusal_report",
            return_value="No evidence found.",
        ):
            result = synthesize_answer(question="Question?", docs=docs)
            assert "No evidence" in result


# ---------------------------------------------------------------------------
# build_evidence_set_from_docs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildEvidenceSetFromDocs:
    """Tests for build_evidence_set_from_docs."""

    def test_basic_extraction(self):
        """Extract evidence items from document list."""
        from riskagent_agenticrag.rag.agentic_primitives import build_evidence_set_from_docs

        docs = [
            Document(
                page_content="FRTB capital charge calculation.",
                metadata={"source": "frtb.md", "chunk_id": "frtb.md:abc123", "start_index": 0},
            ),
            Document(
                page_content="CVA risk overview.",
                metadata={"source": "cva.md", "chunk_id": "cva.md:def456", "start_index": 100},
            ),
        ]
        evidence = build_evidence_set_from_docs(docs, include_text=True)
        assert len(evidence) == 2
        assert evidence[0]["evidence_id"] == "ev_0"
        assert evidence[0]["source"] == "frtb.md"
        assert evidence[0]["chunk_id"] == "frtb.md:abc123"
        assert "text" in evidence[0]
        assert evidence[1]["evidence_id"] == "ev_1"

    def test_include_text_false(self):
        """When include_text=False, 'text' key should be absent."""
        from riskagent_agenticrag.rag.agentic_primitives import build_evidence_set_from_docs

        docs = [Document(page_content="content", metadata={"source": "a.md", "chunk_id": "x", "start_index": 0})]
        evidence = build_evidence_set_from_docs(docs, include_text=False)
        assert "text" not in evidence[0]

    def test_optional_metadata_fields(self):
        """Optional metadata like tool_name and section_path should be included."""
        from riskagent_agenticrag.rag.agentic_primitives import build_evidence_set_from_docs

        docs = [
            Document(
                page_content="Data",
                metadata={
                    "source": "doc.md",
                    "chunk_id": "c1",
                    "start_index": 0,
                    "tool_name": "web_search",
                    "section_path": "Risk / FRTB",
                },
            )
        ]
        evidence = build_evidence_set_from_docs(docs, include_text=False)
        assert evidence[0]["tool_name"] == "web_search"
        assert evidence[0]["section_path"] == "Risk / FRTB"


# ---------------------------------------------------------------------------
# build_claims_from_answer
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildClaimsFromAnswer:
    """Tests for build_claims_from_answer."""

    def test_claim_parsing_with_citations(self):
        """Claims should be extracted from paragraphs with citation markers."""
        from riskagent_agenticrag.rag.agentic_primitives import build_claims_from_answer

        answer = (
            "FRTB introduces new capital requirements.\n\n"
            "Citations: [source=frtb.md chunk_id=frtb_chunk1]\n\n"
            "CVA risk is also affected.\n\n"
            "Citations: [source=cva.md chunk_id=cva_chunk2]"
        )
        evidence_set = [
            {"evidence_id": "ev_0", "chunk_id": "frtb_chunk1", "snippet": "FRTB capital"},
            {"evidence_id": "ev_1", "chunk_id": "cva_chunk2", "snippet": "CVA risk"},
        ]
        claims = build_claims_from_answer(answer, evidence_set=evidence_set)
        assert len(claims) >= 2
        assert claims[0]["claim_id"] == "cl_0"
        assert "ev_0" in claims[0]["evidence_ids"]

    def test_empty_evidence_returns_no_claims(self):
        """Empty evidence_set should return no claims."""
        from riskagent_agenticrag.rag.agentic_primitives import build_claims_from_answer

        claims = build_claims_from_answer("Some answer text.", evidence_set=[])
        assert claims == []

    def test_fallback_matching_when_no_citation_markers(self):
        """Without citation markers, claims use token overlap to assign evidence."""
        from riskagent_agenticrag.rag.agentic_primitives import build_claims_from_answer

        answer = "FRTB delta risk calculation methodology is complex."
        evidence_set = [
            {"evidence_id": "ev_0", "chunk_id": "c1", "snippet": "FRTB delta risk capital"},
            {"evidence_id": "ev_1", "chunk_id": "c2", "snippet": "unrelated weather data"},
        ]
        claims = build_claims_from_answer(answer, evidence_set=evidence_set)
        assert len(claims) == 1
        # Should match ev_0 due to token overlap with "FRTB delta risk"
        assert "ev_0" in claims[0]["evidence_ids"]
