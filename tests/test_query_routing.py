from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest

from riskagent_agenticrag.indexing.indexer import incremental_index
from riskagent_agenticrag.rag.retriever_factory import build_retriever


class TestWeek9QueryRoutingAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step2"
        os.environ.setdefault("RISKAGENT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        os.environ.setdefault("RISKAGENT_DENSE_K", "24")
        os.environ.setdefault("RISKAGENT_SPARSE_K", "24")
        os.environ.setdefault("RISKAGENT_CANDIDATE_K", "50")
        os.environ.setdefault("RISKAGENT_RERANK_K", "30")

        os.environ.setdefault("RISKAGENT_QUERY_EXPANSION_N", "3")
        os.environ.setdefault("RISKAGENT_ENABLE_STEP_BACK", "true")
        os.environ.setdefault("RISKAGENT_ENABLE_DECOMPOSITION", "true")
        os.environ.setdefault("RISKAGENT_PER_QUERY_K", "8")
        os.environ.setdefault("RISKAGENT_QUERY_RRF_K", "60")
        os.environ.setdefault("RISKAGENT_QUERY_MAX_VARIANTS", "6")

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

    def test_step2_query_intelligence_adds_variant_fusion_scores(self) -> None:
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        retriever = build_retriever(persist_dir=self.persist_dir, final_k=4)

        q = "Explain FRTB and Basel II.5 differences and how market risk capital is computed"
        docs = retriever.invoke(q)
        self.assertEqual(len(docs), 4)

        saw_multi_variant = False
        for d in docs:
            meta = d.metadata or {}
            self.assertIn("query_intel_score", meta)
            self.assertIsInstance(meta.get("query_intel_score"), float)
            self.assertIn("query_variants", meta)
            self.assertIsInstance(meta.get("query_variants"), list)
            if len(meta.get("query_variants") or []) >= 2:
                saw_multi_variant = True

            self.assertIn("rrf_score", meta)
            self.assertIn("coarse_score", meta)
            self.assertIn("rerank_score", meta)
            self.assertIsInstance(meta.get("rrf_score"), float)
            self.assertIsInstance(meta.get("coarse_score"), float)
            self.assertIsInstance(meta.get("rerank_score"), float)

        self.assertTrue(saw_multi_variant)


if __name__ == "__main__":
    unittest.main()
