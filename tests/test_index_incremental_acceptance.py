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


class TestIncrementalIndexAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")
        os.environ.setdefault("RISKAGENT_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = pathlib.Path(self._tmp.name) / "corpus"
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"

        src_root = self.project_root / "corpus"
        src = src_root / "Background.md"
        dst = self.corpus_dir / src.relative_to(src_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_incremental_index_skips_unchanged_sources(self) -> None:
        r1 = incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        self.assertGreaterEqual(len(r1.indexed_sources), 1)
        self.assertGreater(r1.chunk_indexed, 0)

        r2 = incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)
        self.assertEqual(len(r2.indexed_sources), 0)
        self.assertGreaterEqual(len(r2.skipped_sources), 1)


if __name__ == "__main__":
    unittest.main()

