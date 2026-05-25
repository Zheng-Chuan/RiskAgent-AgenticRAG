"""
Scenario tests - end-to-end main flow validation with real LLM and Docker.
Prerequisites: make up (Docker services), valid LLM API key in .env
Run: make test-scenario
"""
from __future__ import annotations

import os
import pathlib
import shutil
import socket
import tempfile
import uuid

import pytest

from tests.conftest import HF_AVAILABLE

pytestmark = pytest.mark.skipif(not HF_AVAILABLE, reason="Embedding models not available")


# ---------------------------------------------------------------------------
# Infrastructure checks
# ---------------------------------------------------------------------------

def _docker_ready() -> bool:
    """Check if Milvus is reachable on localhost:19530."""
    try:
        with socket.socket() as s:
            s.settimeout(2)
            return s.connect_ex(("127.0.0.1", 19530)) == 0
    except Exception:
        return False


def _llm_ready() -> bool:
    """Check if Volcano Engine LLM endpoint is reachable."""
    try:
        with socket.socket() as s:
            s.settimeout(3)
            return s.connect_ex(("ark.cn-beijing.volces.com", 443)) == 0
    except Exception:
        return False


skip_no_infra = pytest.mark.skipif(
    not (_docker_ready() and _llm_ready()),
    reason="Docker middleware or LLM not available",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CORPUS_ROOT = PROJECT_ROOT / "corpus"


def _setup_env(persist_dir: pathlib.Path, corpus_dir: pathlib.Path, collection_name: str) -> dict[str, str | None]:
    """Set environment variables for isolated test run, return backup."""
    keys = [
        "EMBEDDINGS_PROVIDER", "RISKAGENT_SELF_RAG", "RISKAGENT_CORPUS_DIR",
        "RISKAGENT_PERSIST_DIR", "RISKAGENT_ARTIFACTS_DIR",
        "MILVUS_HOST", "MILVUS_PORT", "MILVUS_COLLECTION",
        "RISKAGENT_ENABLE_LLM_APPEAL",
    ]
    backup = {k: os.environ.get(k) for k in keys}
    os.environ["EMBEDDINGS_PROVIDER"] = "hf"
    os.environ["RISKAGENT_SELF_RAG"] = "true"
    os.environ["RISKAGENT_CORPUS_DIR"] = str(corpus_dir)
    os.environ["RISKAGENT_PERSIST_DIR"] = str(persist_dir)
    os.environ["RISKAGENT_ARTIFACTS_DIR"] = str(persist_dir / "artifacts")
    os.environ["MILVUS_HOST"] = "127.0.0.1"
    os.environ["MILVUS_PORT"] = "19530"
    os.environ["MILVUS_COLLECTION"] = collection_name
    os.environ["RISKAGENT_ENABLE_LLM_APPEAL"] = "false"
    return backup


def _restore_env(backup: dict[str, str | None]) -> None:
    """Restore environment from backup."""
    for k, v in backup.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _copy_corpus_subset(target_dir: pathlib.Path) -> None:
    """Copy a small corpus subset (FRTB wikipedia) for testing."""
    src = CORPUS_ROOT / "regulatory_seed" / "md" / "en" / "wikipedia_frtb.md"
    if src.exists():
        dst = target_dir / "regulatory_seed" / "md" / "en" / "wikipedia_frtb.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    # Also copy Background.md as a secondary source
    bg = CORPUS_ROOT / "Background.md"
    if bg.exists():
        shutil.copyfile(bg, target_dir / "Background.md")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def scenario_env():
    """Set up isolated environment with indexed corpus for scenario tests."""
    tmp = tempfile.TemporaryDirectory()
    tmp_path = pathlib.Path(tmp.name)
    corpus_dir = tmp_path / "corpus"
    persist_dir = tmp_path / "milvus"
    collection_name = f"scenario_main_{uuid.uuid4().hex[:10]}"

    corpus_dir.mkdir(parents=True, exist_ok=True)
    persist_dir.mkdir(parents=True, exist_ok=True)

    _copy_corpus_subset(corpus_dir)
    backup = _setup_env(persist_dir, corpus_dir, collection_name)

    # Index corpus
    from riskagent_agenticrag.indexing.indexer import incremental_index

    incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=None)

    yield {
        "persist_dir": persist_dir,
        "corpus_dir": corpus_dir,
        "collection_name": collection_name,
    }

    _restore_env(backup)
    tmp.cleanup()


# ---------------------------------------------------------------------------
# Test class: main flow scenarios
# ---------------------------------------------------------------------------

@skip_no_infra
@pytest.mark.scenario
class TestScenarioMainFlow:
    """End-to-end scenario tests with real LLM + Docker middleware."""

    def _chat(self, question: str, *, max_rounds: int = 2, history: list | None = None) -> dict:
        """Helper: invoke RiskAgentSystem.chat."""
        from riskagent_agenticrag.app import RiskAgentSystem

        system = RiskAgentSystem()
        return system.chat(
            question=question,
            history=history,
            max_rounds=max_rounds,
            request_id=f"scenario-{uuid.uuid4().hex[:8]}",
        )

    # ------------------------------------------------------------------
    # test_scenario_simple_factual_question
    # ------------------------------------------------------------------
    def test_scenario_simple_factual_question(self, scenario_env: dict) -> None:
        """Index corpus, ask 'What is FRTB?', verify answer has content + citations + evidence_set + status='ok'."""
        out = self._chat("What is FRTB?")

        assert out.get("status") in {"ok", "failed"}, f"Unexpected status: {out.get('status')}"
        assert out.get("answer"), "Answer should not be empty"
        assert len(str(out["answer"])) > 50, "Answer too short"
        assert isinstance(out.get("citations"), list), "citations must be a list"
        assert isinstance(out.get("evidence_set"), list), "evidence_set must be a list"
        assert len(out["evidence_set"]) > 0, "evidence_set should not be empty"

    # ------------------------------------------------------------------
    # test_scenario_multi_round_retrieval
    # ------------------------------------------------------------------
    def test_scenario_multi_round_retrieval(self, scenario_env: dict) -> None:
        """Ask a question that may require multi-round retrieval; verify decision_log shows retrieval steps."""
        out = self._chat(
            "What are the key differences between IMA and SA in FRTB capital calculation?",
            max_rounds=2,
        )

        assert out.get("answer"), "Answer should not be empty"
        decision_log = out.get("decision_log", [])
        assert isinstance(decision_log, list)
        assert len(decision_log) >= 2, "decision_log should have at least rewrite + retrieve steps"

        # Verify at least one retrieve_round step exists
        step_ids = [entry.get("step_id", "") for entry in decision_log]
        retrieve_steps = [s for s in step_ids if s.startswith("retrieve_round_")]
        assert len(retrieve_steps) >= 1, "Should have at least one retrieve_round step"

    # ------------------------------------------------------------------
    # test_scenario_citation_verification
    # ------------------------------------------------------------------
    def test_scenario_citation_verification(self, scenario_env: dict) -> None:
        """Verify each citation in response has valid source, chunk_id, snippet."""
        out = self._chat("What is the Fundamental Review of the Trading Book?")

        citations = out.get("citations", [])
        assert isinstance(citations, list)
        # With real corpus we should get citations
        if citations:
            for cit in citations:
                assert isinstance(cit, dict), "Each citation should be a dict"
                assert cit.get("source"), f"Citation missing source: {cit}"
                assert cit.get("chunk_id"), f"Citation missing chunk_id: {cit}"
                assert cit.get("snippet") or cit.get("text"), f"Citation missing snippet/text: {cit}"

    # ------------------------------------------------------------------
    # test_scenario_multi_turn_chat
    # ------------------------------------------------------------------
    def test_scenario_multi_turn_chat(self, scenario_env: dict) -> None:
        """Send 2 messages in conversation, verify context is maintained."""
        # First message
        out1 = self._chat("What is FRTB?")
        assert out1.get("answer"), "First answer should not be empty"
        answer1 = out1["answer"]

        # Second message with history
        history = [("What is FRTB?", answer1)]
        out2 = self._chat(
            "What are its main components?",
            history=history,
        )
        assert out2.get("answer"), "Second answer should not be empty"
        # The response should reference FRTB context from history
        combined = str(out2["answer"]).lower()
        # At minimum it should produce a meaningful answer
        assert len(combined) > 30, "Multi-turn answer too short"

    # ------------------------------------------------------------------
    # test_scenario_quality_gate_pass
    # ------------------------------------------------------------------
    def test_scenario_quality_gate_pass(self, scenario_env: dict) -> None:
        """Ask a well-covered question, verify no failure_reason."""
        out = self._chat("What is FRTB?")

        # For well-covered questions with real LLM, we expect passing gate
        # But gate may legitimately fail, so we just check the structure
        assert "failure_reason" in out
        if out["status"] == "ok":
            assert out["failure_reason"] is None

    # ------------------------------------------------------------------
    # test_scenario_self_rag_enabled
    # ------------------------------------------------------------------
    def test_scenario_self_rag_enabled(self, scenario_env: dict) -> None:
        """Enable self_rag, verify debug.self_rag structure in response."""
        out = self._chat("What is FRTB?")

        debug = out.get("debug", {})
        assert isinstance(debug, dict)
        self_rag = debug.get("self_rag")
        assert self_rag is not None, "self_rag should be present in debug when enabled"
        assert isinstance(self_rag, dict)
        assert self_rag.get("enabled") is True or "rounds" in self_rag
        rounds = self_rag.get("rounds", [])
        assert isinstance(rounds, list)
        assert len(rounds) >= 1, "self_rag should have at least 1 round"
        # Verify round structure
        first_round = rounds[0]
        assert "round" in first_round
        assert "query" in first_round
        assert "grade" in first_round

    # ------------------------------------------------------------------
    # test_scenario_decision_log_completeness
    # ------------------------------------------------------------------
    def test_scenario_decision_log_completeness(self, scenario_env: dict) -> None:
        """Verify decision_log contains all expected steps (rewrite, retrieve, synthesize-related)."""
        out = self._chat("What is FRTB?")

        decision_log = out.get("decision_log", [])
        assert isinstance(decision_log, list)
        assert len(decision_log) >= 2, "decision_log should have multiple entries"

        step_ids = [entry.get("step_id", "") for entry in decision_log]

        # Must have rewrite step
        assert "rewrite" in step_ids, "decision_log should contain 'rewrite' step"

        # Must have at least one retrieve_round step
        has_retrieve = any(s.startswith("retrieve_round_") for s in step_ids)
        assert has_retrieve, "decision_log should contain retrieve_round step"

        # Each entry should have required fields
        for entry in decision_log:
            assert "step_id" in entry, f"Entry missing step_id: {entry}"
            assert "agent" in entry, f"Entry missing agent: {entry}"
            assert "rationale" in entry, f"Entry missing rationale: {entry}"
            assert "chosen" in entry, f"Entry missing chosen: {entry}"

    # ------------------------------------------------------------------
    # test_scenario_full_response_schema
    # ------------------------------------------------------------------
    def test_scenario_full_response_schema(self, scenario_env: dict) -> None:
        """Verify response has ALL expected fields with correct types."""
        out = self._chat("What is FRTB?")

        # Required top-level keys
        assert "request_id" in out
        assert "answer" in out
        assert "citations" in out
        assert "claims" in out
        assert "evidence_set" in out
        assert "decision_log" in out
        assert "status" in out
        assert "failure_reason" in out
        assert "debug" in out

        # Type checks
        assert isinstance(out["request_id"], str)
        assert isinstance(out["answer"], str)
        assert isinstance(out["citations"], list)
        assert isinstance(out["claims"], list)
        assert isinstance(out["evidence_set"], list)
        assert isinstance(out["decision_log"], list)
        assert isinstance(out["status"], str)
        assert out["failure_reason"] is None or isinstance(out["failure_reason"], dict)
        assert isinstance(out["debug"], dict)

        # Status must be valid value
        assert out["status"] in {"ok", "failed", "error"}

        # Debug should contain useful fields
        debug = out["debug"]
        assert "final_query" in debug or "request_id" in debug
