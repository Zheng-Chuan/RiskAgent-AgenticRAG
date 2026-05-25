from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest

import pytest

from tests.conftest import HF_AVAILABLE

pytestmark = pytest.mark.skipif(not HF_AVAILABLE, reason="Embedding models not available")

from riskagent_agenticrag.indexing.indexer import incremental_index
from riskagent_agenticrag.rag.advanced_index import advanced_index_stats
from riskagent_agenticrag.rag.retriever_factory import build_retriever


class TestWeek10AdvancedIndexingAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

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
            src_root / "regulatory_seed" / "md" / "en" / "wikipedia_frtb.md",
        ]
        for src in files:
            rel = src.relative_to(src_root)
            dst = self.corpus_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    def test_unified_pipeline_builds_advanced_indices_and_expands_parent_context(self) -> None:
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        stats = advanced_index_stats(persist_dir=self.persist_dir)
        self.assertGreater(stats.get("parents", 0), 0)
        self.assertGreater(stats.get("summaries", 0), 0)
        self.assertGreater(stats.get("hydes", 0), 0)

        retriever = build_retriever(persist_dir=self.persist_dir, final_k=4)

        q = "Explain the high level goals of FRTB and why Basel II.5 was insufficient"
        docs = retriever.invoke(q)
        self.assertEqual(len(docs), 4)

        saw_expanded = False
        saw_adv_score = False
        for d in docs:
            meta = d.metadata or {}
            self.assertIn("parent_id", meta)
            self.assertIn("advanced_index_score", meta)
            self.assertIsInstance(meta.get("advanced_index_score"), float)
            saw_adv_score = True

            expanded = str(meta.get("expanded_text") or "")
            if expanded and len(expanded) > len((d.page_content or "")):
                saw_expanded = True

            sources = meta.get("indexing_sources") or []
            self.assertIsInstance(sources, list)

        self.assertTrue(saw_adv_score)
        self.assertTrue(saw_expanded)


if __name__ == "__main__":
    unittest.main()
