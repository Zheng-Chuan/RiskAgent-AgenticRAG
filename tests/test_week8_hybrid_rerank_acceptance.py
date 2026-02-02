from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest

from riskagent_rag.indexing.indexer import incremental_index
from riskagent_rag.rag.retriever_factory import build_retriever


class TestWeek8HybridRerankAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        os.environ["RISKAGENT_RETRIEVER_MODE"] = "hybrid_rerank"
        os.environ.setdefault("RISKAGENT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        os.environ.setdefault("RISKAGENT_DENSE_K", "20")
        os.environ.setdefault("RISKAGENT_SPARSE_K", "20")
        os.environ.setdefault("RISKAGENT_CANDIDATE_K", "30")

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
        ]
        for src in files:
            rel = src.relative_to(src_root)
            dst = self.corpus_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    def test_hybrid_rerank_uses_sparse_and_dense_and_scores(self) -> None:
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        retriever = build_retriever(persist_dir=self.persist_dir, final_k=4)

        docs = retriever.invoke("Basel II.5 framework market risk capital rules")
        self.assertTrue(docs)

        sources: set[str] = set()
        for d in docs:
            meta = d.metadata or {}
            srcs = meta.get("retrieval_sources") or []
            if isinstance(srcs, list):
                for s in srcs:
                    sources.add(str(s))
            self.assertIn("rerank_score", meta)
            self.assertIsInstance(meta.get("rerank_score"), float)

        self.assertIn("dense", sources)
        self.assertIn("sparse", sources)


if __name__ == "__main__":
    unittest.main()
