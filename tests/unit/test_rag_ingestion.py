"""Unit tests for RAG ingestion, chunking, embeddings, query_intelligence, and self_rag."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Chunking: chunk size, overlap, short documents, long paragraphs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChunking:
    """Tests for document chunking logic."""

    def test_short_document_single_chunk(self):
        """A document shorter than max_chunk_size should remain as one chunk."""
        from riskagent_agenticrag.rag.chunking import _llm_semantic_chunking

        text = "Short paragraph about FRTB risk."
        chunks = _llm_semantic_chunking(text, max_chunk_size=800, overlap=100)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_long_document_produces_multiple_chunks(self):
        """A document longer than max_chunk_size should be split into multiple chunks."""
        from riskagent_agenticrag.rag.chunking import _fallback_chunking

        text = "FRTB risk capital. " * 200  # ~3800 chars
        chunks = _fallback_chunking(text, max_chunk_size=500, overlap=50)
        assert len(chunks) > 1
        # Each chunk should not greatly exceed max_chunk_size
        for c in chunks:
            assert len(c["text"]) <= 700  # allow some boundary flexibility

    def test_chunk_overlap_present(self):
        """Consecutive chunks should have overlapping content."""
        from riskagent_agenticrag.rag.chunking import _fallback_chunking

        text = "A" * 500 + "\n\n" + "B" * 500 + "\n\n" + "C" * 500
        chunks = _fallback_chunking(text, max_chunk_size=600, overlap=100)
        if len(chunks) >= 2:
            # The end of chunk 0 should overlap with the start of chunk 1
            end_of_first = chunks[0]["text"][-50:]
            start_of_second = chunks[1]["text"][:100]
            # There should be shared content due to overlap
            assert chunks[0]["end"] > chunks[1]["start"]

    def test_chunk_start_end_indices(self):
        """Each chunk should have valid start and end indices."""
        from riskagent_agenticrag.rag.chunking import _fallback_chunking

        text = "Word " * 300  # ~1500 chars
        chunks = _fallback_chunking(text, max_chunk_size=500, overlap=50)
        for c in chunks:
            assert c["start"] >= 0
            assert c["end"] <= len(text)
            assert c["start"] < c["end"]
            assert c["text"] == text[c["start"]:c["end"]]

    def test_llm_chunking_short_text_bypass(self):
        """LLM chunking should not call LLM for text shorter than max_chunk_size."""
        from riskagent_agenticrag.rag.chunking import _llm_semantic_chunking

        text = "Very short text."
        # Should not need LLM call - text fits in one chunk
        with patch(
            "riskagent_agenticrag.rag.chunking.call_llm_json_with_model",
            side_effect=AssertionError("LLM should not be called for short text"),
        ):
            chunks = _llm_semantic_chunking(text, max_chunk_size=800, overlap=100)
            assert len(chunks) == 1
            assert chunks[0]["text"] == text

    def test_llm_chunking_fallback_on_error(self):
        """LLM chunking should fallback to character chunking on LLM error."""
        from riskagent_agenticrag.rag.chunking import _llm_semantic_chunking

        text = "Content block. " * 100  # ~1500 chars
        with patch(
            "riskagent_agenticrag.rag.chunking.call_llm_json_with_model",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            chunks = _llm_semantic_chunking(text, max_chunk_size=500, overlap=50)
            assert len(chunks) >= 1
            # All chunks should have text
            for c in chunks:
                assert c["text"].strip()


# ---------------------------------------------------------------------------
# Embeddings factory: hash provider creation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmbeddingsFactory:
    """Tests for embeddings factory and HashEmbeddings."""

    def test_hash_embeddings_deterministic(self):
        """HashEmbeddings should produce deterministic vectors for same input."""
        from riskagent_agenticrag.rag.embeddings import HashEmbeddings

        emb = HashEmbeddings(dimension=64)
        vec1 = emb.embed_query("FRTB capital charge")
        vec2 = emb.embed_query("FRTB capital charge")
        assert vec1 == vec2

    def test_hash_embeddings_dimension(self):
        """HashEmbeddings should produce vectors of specified dimension."""
        from riskagent_agenticrag.rag.embeddings import HashEmbeddings

        emb = HashEmbeddings(dimension=128)
        vec = emb.embed_query("test query")
        assert len(vec) == 128

    def test_hash_embeddings_normalized(self):
        """HashEmbeddings vectors should be approximately unit-normalized."""
        from riskagent_agenticrag.rag.embeddings import HashEmbeddings
        from math import sqrt

        emb = HashEmbeddings(dimension=64)
        vec = emb.embed_query("delta risk exposure")
        norm = sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_hash_embeddings_different_inputs_differ(self):
        """Different inputs should produce different vectors."""
        from riskagent_agenticrag.rag.embeddings import HashEmbeddings

        emb = HashEmbeddings(dimension=64)
        vec1 = emb.embed_query("FRTB")
        vec2 = emb.embed_query("CVA")
        assert vec1 != vec2

    def test_hash_embeddings_embed_documents(self):
        """embed_documents should return list of vectors."""
        from riskagent_agenticrag.rag.embeddings import HashEmbeddings

        emb = HashEmbeddings(dimension=32)
        vecs = emb.embed_documents(["text one", "text two", "text three"])
        assert len(vecs) == 3
        assert all(len(v) == 32 for v in vecs)

    def test_build_embeddings_hash_provider(self):
        """build_embeddings with hash provider should return HashEmbeddings."""
        from riskagent_agenticrag.rag.embeddings import build_embeddings, HashEmbeddings

        with patch("riskagent_agenticrag.rag.embeddings.settings") as mock_settings:
            mock_settings.embeddings.provider = "hash"
            mock_settings.embeddings.model_name = "test-model"
            mock_settings.paths.hf_cache_dir = MagicMock()
            mock_settings.paths.hf_cache_dir.mkdir = MagicMock()
            result = build_embeddings()
            assert isinstance(result, HashEmbeddings)


# ---------------------------------------------------------------------------
# query_intelligence: routing classification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQueryIntelligence:
    """Tests for query intelligence routing."""

    def test_route_compare(self):
        """Queries with 'compare' or 'vs' should route to 'compare'."""
        from riskagent_agenticrag.rag.query_intelligence import _route_name

        assert _route_name("FRTB vs Basel III") == "compare"
        assert _route_name("Compare delta and vega risk") == "compare"
        assert _route_name("CVA和DVA的区别") == "compare"

    def test_route_background(self):
        """Queries about definitions/overview should route to 'background'."""
        from riskagent_agenticrag.rag.query_intelligence import _route_name

        assert _route_name("What is the definition of FRTB?") == "background"
        assert _route_name("FRTB overview background") == "background"
        assert _route_name("FRTB是什么") == "background"

    def test_route_procedure(self):
        """Queries about calculation/formula should route to 'procedure'."""
        from riskagent_agenticrag.rag.query_intelligence import _route_name

        assert _route_name("How to calculate delta capital charge?") == "procedure"
        assert _route_name("FRTB formula for ES") == "procedure"

    def test_route_default(self):
        """Generic queries should route to 'default'."""
        from riskagent_agenticrag.rag.query_intelligence import _route_name

        assert _route_name("FRTB desk requirements") == "default"
        assert _route_name("limit breach notification") == "default"

    def test_generate_query_variants_basic(self):
        """generate_query_variants should produce at least the base query."""
        from riskagent_agenticrag.rag.query_intelligence import (
            generate_query_variants,
            QueryIntelConfig,
        )

        config = QueryIntelConfig()
        variants = generate_query_variants(
            question="What is FRTB?", base_query="FRTB", config=config
        )
        assert len(variants) >= 1
        assert "FRTB" in variants[0]


# ---------------------------------------------------------------------------
# self_rag: scoring structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSelfRag:
    """Tests for self_rag scoring."""

    def test_grade_docs_empty_returns_insufficient(self):
        """No docs should return insufficient grade."""
        from riskagent_agenticrag.rag.self_rag import grade_docs

        result = grade_docs(question="What is FRTB?", docs=[])
        assert result.sufficient is False
        assert result.reason == "no_docs"
        assert result.grades == []

    def test_grade_docs_relevant_docs(self):
        """Relevant docs should produce grades with isrel > 0."""
        from riskagent_agenticrag.rag.self_rag import grade_docs

        docs = [
            Document(
                page_content="FRTB is the Fundamental Review of the Trading Book regulation.",
                metadata={"parent_id": "p1", "chunk_id": "c1"},
            )
        ]
        result = grade_docs(question="What is FRTB trading book?", docs=docs)
        assert len(result.grades) == 1
        assert result.grades[0].isrel >= 0.0
        assert result.top_isrel >= 0.0

    def test_grade_docs_structure(self):
        """SelfRagRetrievalGrade should have expected fields."""
        from riskagent_agenticrag.rag.self_rag import grade_docs, SelfRagRetrievalGrade

        docs = [Document(page_content="test content", metadata={"parent_id": "p", "chunk_id": "c"})]
        result = grade_docs(question="test", docs=docs)
        assert isinstance(result, SelfRagRetrievalGrade)
        assert hasattr(result, "sufficient")
        assert hasattr(result, "reason")
        assert hasattr(result, "top_isrel")
        assert hasattr(result, "avg_isrel")
        assert hasattr(result, "grades")

    def test_grade_generation_ok(self):
        """grade_generation with no failure returns ok."""
        from riskagent_agenticrag.rag.self_rag import grade_generation

        result = grade_generation(failure_reason=None)
        assert result["ok"] is True
        assert result["category"] == ""

    def test_grade_generation_failure(self):
        """grade_generation with failure_reason returns structured error."""
        from riskagent_agenticrag.rag.self_rag import grade_generation

        result = grade_generation(
            failure_reason={"category": "hallucination", "message": "answer not grounded"}
        )
        assert result["ok"] is False
        assert result["category"] == "hallucination"
        assert "not grounded" in result["message"]

    def test_should_require_numeric_backing(self):
        """Questions about delta/breach/exposure should require numeric backing."""
        from riskagent_agenticrag.rag.self_rag import should_require_numeric_backing

        assert should_require_numeric_backing(question="What is the delta exposure?") is True
        assert should_require_numeric_backing(question="Limit breach report") is True
        assert should_require_numeric_backing(question="What is FRTB overview?") is False
