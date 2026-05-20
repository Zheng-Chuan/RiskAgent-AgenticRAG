from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest

from unittest.mock import patch

from riskagent_agenticrag.indexing.indexer import incremental_index
from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat
from riskagent_agenticrag.rag.retriever_factory import build_retriever


class TestWeek11SelfRagAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        os.environ["RISKAGENT_SELF_RAG"] = "true"
        os.environ.setdefault("RISKAGENT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        os.environ.setdefault("RISKAGENT_DENSE_K", "24")
        os.environ.setdefault("RISKAGENT_SPARSE_K", "24")
        os.environ.setdefault("RISKAGENT_CANDIDATE_K", "60")
        os.environ.setdefault("RISKAGENT_RERANK_K", "40")
        os.environ.setdefault("RISKAGENT_STEP3_BASE_FINAL_K", "12")
        os.environ.setdefault("RISKAGENT_STEP3_SUMMARY_K", "12")
        os.environ.setdefault("RISKAGENT_STEP3_HYDE_K", "12")
        os.environ.setdefault("RISKAGENT_STEP3_EXPAND_PARENT", "true")

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = pathlib.Path(self._tmp.name) / "corpus"
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        self._prepare_real_corpus_subset()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _prepare_real_corpus_subset(self) -> None:
        src_root = self.project_root / "corpus"
        files = [
            src_root / "Background.md",
            src_root / "acceptance" / "frtb_icma.md",
            src_root / "acceptance" / "cva_cfi.md",
            src_root / "regulatory_seed" / "md" / "en" / "wikipedia_frtb.md",
        ]
        for src in files:
            rel = src.relative_to(src_root)
            dst = self.corpus_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    def test_self_rag_emits_grades_and_returns_ok(self) -> None:
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        retriever = build_retriever(persist_dir=self.persist_dir, final_k=4)

        q = "Explain why FRTB was introduced after the 2008 crisis and how it relates to Basel II.5"
        fake_json = {
            "query": "FRTB Basel II.5 crisis background",
        }

        def _fake_llm_json(prompt: str, temperature: float = 0.0):
            p = str(prompt or "")
            if "\"query\"" in p and "Schema" in p:
                return {"query": "FRTB Basel II.5 crisis background"}
            if "\"sufficient\"" in p and "Schema" in p:
                return {"sufficient": True, "improved_query": "", "reason": "ok"}
            if "\"should_call_tool\"" in p and "Schema" in p:
                return {"should_call_tool": False, "args": {}, "reason": "not needed"}
            return fake_json

        def _fake_llm_text(prompt: str, temperature: float = 0.0):
            return "## TLDR\n- ok\n\n## Concept\nok\n\n## Why it matters\nok\n\n## Data flow / fields\nok\n\n## Example\nok\n\n## Citations\nok"

        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=_fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=_fake_llm_text
        ), patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=_fake_llm_text):
            out = run_langgraph_agentic_chat(question=q, retriever=retriever, max_rounds=2)

        self.assertIn(out.get("status"), {"ok", "failed"})

        debug = out.get("debug") or {}
        self.assertIsInstance(debug, dict)
        self.assertIn("self_rag", debug)
        sr = debug.get("self_rag") or {}
        self.assertTrue(bool(sr.get("enabled")))
        self.assertIn("generation", sr)

        decisions = out.get("decision_log") or []
        self.assertIsInstance(decisions, list)
        step_ids = [str(d.get("step_id") or "") for d in decisions if isinstance(d, dict)]
        self.assertTrue(any(s.startswith("self_rag_grade_docs_round_") for s in step_ids))
        self.assertIn("self_rag_grade_generation", step_ids)


if __name__ == "__main__":
    unittest.main()
