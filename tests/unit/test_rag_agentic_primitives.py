"""Unit tests for RAG agentic primitives."""

from __future__ import annotations

from unittest.mock import patch

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

    def test_fallback_returns_original_when_json_call_fails(self):
        """If LLM JSON parsing fails, rewrite_query should keep the original question."""
        from riskagent_agenticrag.rag.agentic_primitives import rewrite_query

        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            side_effect=RuntimeError("LLM did not return valid JSON"),
        ):
            result = rewrite_query("What is CVA capital?")
            assert result == "What is CVA capital?"


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

    def test_json_failure_falls_back_to_heuristic_continue(self):
        """If critique JSON parsing fails, use heuristic insufficiency instead of crashing."""
        from riskagent_agenticrag.rag.agentic_primitives import critique_retrieval

        docs = [Document(page_content="Short unrelated weather paragraph about rain and wind.")]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            side_effect=RuntimeError("LLM did not return valid JSON"),
        ):
            sufficient, improved_query, reason = critique_retrieval("FRTB capital?", docs)

        assert sufficient is False
        assert improved_query == "FRTB capital?"
        assert "json_parse_fallback_heuristic_insufficient" in reason

    def test_json_failure_falls_back_to_heuristic_stop(self):
        """If critique JSON parsing fails on good evidence, use heuristic sufficiency."""
        from riskagent_agenticrag.rag.agentic_primitives import critique_retrieval

        docs = [Document(page_content="FRTB capital requirement for market risk uses standardized and internal model approaches.")]
        with patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_json",
            side_effect=RuntimeError("LLM did not return valid JSON"),
        ):
            sufficient, improved_query, reason = critique_retrieval("What is FRTB capital requirement?", docs)

        assert sufficient is True
        assert improved_query == ""
        assert "json_parse_fallback_heuristic_sufficient" in reason


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


@pytest.mark.unit
class TestGenerateAnswerSanitization:
    """Tests for answer post-processing that removes weak meta statements."""

    def test_generate_answer_sanitizes_unsupported_meta_lines(self):
        from riskagent_agenticrag.llm.generate import generate_answer

        docs = [Document(page_content="FRTB is a market risk framework introduced after Basel II.5 shortcomings.")]
        raw = (
            "1) TLDR\n"
            "- FRTB is a market risk framework.\n\n"
            "3) Why it matters\n"
            "- The context does not discuss why it matters.\n"
            "Next actions: read more sources."
        )
        with patch("riskagent_agenticrag.llm.generate.call_llm_text", return_value=raw):
            result = generate_answer("What is FRTB?", docs)

        assert "FRTB is a market risk framework" in result
        assert "The context does not discuss" not in result
        assert "Next actions" not in result


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

    def test_prefers_expanded_text_and_keeps_longer_snippet(self):
        """Expanded text should be preferred so numeric support is not truncated too early."""
        from riskagent_agenticrag.rag.agentic_primitives import build_evidence_set_from_docs

        docs = [
            Document(
                page_content="short body",
                metadata={
                    "source": "doc.md",
                    "chunk_id": "c1",
                    "start_index": 0,
                    "expanded_text": "LGD is 100 percent for equity and 75 percent for senior debt instruments.",
                },
            )
        ]
        evidence = build_evidence_set_from_docs(docs, include_text=True)
        assert "75 percent" in evidence[0]["snippet"]
        assert "75 percent" in evidence[0]["text"]


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

    def test_claims_use_following_citations_block(self):
        """A paragraph should inherit chunk citations from the next Citations block."""
        from riskagent_agenticrag.rag.agentic_primitives import build_claims_from_answer

        answer = (
            "LGD is 100 percent for equity instruments.\n"
            "- Senior debt instruments use 75 percent.\n\n"
            "Citations: [source=doc.md chunk_id=doc_chunk_1]"
        )
        evidence_set = [
            {"evidence_id": "ev_0", "chunk_id": "doc_chunk_1", "snippet": "LGD is 100 percent for equity instruments and 75 percent for senior debt."}
        ]

        claims = build_claims_from_answer(answer, evidence_set=evidence_set)
        assert len(claims) == 2
        assert claims[0]["evidence_ids"] == ["ev_0"]
        assert claims[1]["evidence_ids"] == ["ev_0"]

    def test_claims_split_bullets_into_separate_claims(self):
        """Bullet lines should become separate claims instead of a single oversized paragraph claim."""
        from riskagent_agenticrag.rag.agentic_primitives import build_claims_from_answer

        answer = (
            "1) TLDR\n"
            "- FRTB is a market risk framework.\n"
            "- It replaced Basel II.5 in important areas.\n\n"
            "Citations: [source=doc.md chunk_id=frtb_chunk]"
        )
        evidence_set = [
            {"evidence_id": "ev_0", "chunk_id": "frtb_chunk", "snippet": "FRTB is a market risk framework that replaced Basel II.5."}
        ]

        claims = build_claims_from_answer(answer, evidence_set=evidence_set)
        assert len(claims) == 2
        assert claims[0]["statement"] == "FRTB is a market risk framework."
        assert claims[1]["statement"] == "It replaced Basel II.5 in important areas."
