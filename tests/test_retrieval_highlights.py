from __future__ import annotations

import collections
import os
import pathlib
import shutil
import tempfile
import unittest

import pytest

from tests.conftest import HF_AVAILABLE

pytestmark = pytest.mark.skipif(not HF_AVAILABLE, reason="Embedding models not available")

from riskagent_agenticrag.indexing.indexer import incremental_index
from riskagent_agenticrag.rag.retriever_factory import build_retriever


class TestWeek8RetrievalHighlightsAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        os.environ.setdefault("RISKAGENT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        os.environ.setdefault("RISKAGENT_DENSE_K", "30")
        os.environ.setdefault("RISKAGENT_SPARSE_K", "30")
        os.environ.setdefault("RISKAGENT_CANDIDATE_K", "60")
        os.environ.setdefault("RISKAGENT_RERANK_K", "40")
        os.environ.setdefault("RISKAGENT_MIN_CHUNK_CHARS", "80")
        os.environ.setdefault("RISKAGENT_MAX_PER_SOURCE", "2")
        os.environ.setdefault("RISKAGENT_MAX_PER_SECTION", "1")

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

    def test_hybrid_has_coarse_and_rerank_and_diversity_constraints(self) -> None:
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        retriever = build_retriever(persist_dir=self.persist_dir, final_k=4)

        q = "FRTB Basel Committee January 2016 minimum capital requirements market risk Basel II.5"
        docs = retriever.invoke(q)
        self.assertEqual(len(docs), 4)

        sources: list[str] = []
        for d in docs:
            text = (d.page_content or "").strip()
            self.assertGreaterEqual(len(text), 80)

            meta = d.metadata or {}
            self.assertIn("rrf_score", meta)
            self.assertIn("coarse_score", meta)
            self.assertIn("rerank_score", meta)
            self.assertIsInstance(meta.get("rrf_score"), float)
            self.assertIsInstance(meta.get("coarse_score"), float)
            self.assertIsInstance(meta.get("rerank_score"), float)

            srcs = meta.get("retrieval_sources") or []
            self.assertIsInstance(srcs, list)
            self.assertTrue(any(s in ("dense", "sparse") for s in srcs))

            sources.append(str(meta.get("source", "")))

        unique_sources = {s for s in sources if s}
        self.assertGreaterEqual(len(unique_sources), 2)

        counter = collections.Counter([s for s in sources if s])
        self.assertLessEqual(max(counter.values(), default=0), 2)


if __name__ == "__main__":
    unittest.main()
