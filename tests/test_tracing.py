from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pytest

from tests.conftest import HF_AVAILABLE

pytestmark = pytest.mark.skipif(not HF_AVAILABLE, reason="Embedding models not available")

from fastapi.testclient import TestClient

from riskagent_agenticrag.api.server import app
from riskagent_agenticrag.indexing.indexer import incremental_index


class TestWeek13TraceAcceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")
        os.environ["OPENAI_API_KEY"] = "test_key"
        os.environ.setdefault("LLM_MODEL", "test_model")
        os.environ.setdefault("LLM_BASE_URL", "http://example.invalid")
        os.environ["RISKAGENT_API_KEY"] = "k"

        self._tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = pathlib.Path(self._tmp.name) / "corpus"
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        self.artifacts_dir = pathlib.Path(self._tmp.name) / "artifacts"
        os.environ["RISKAGENT_CORPUS_DIR"] = str(self.corpus_dir)
        os.environ["RISKAGENT_PERSIST_DIR"] = str(self.persist_dir)
        os.environ["RISKAGENT_ARTIFACTS_DIR"] = str(self.artifacts_dir)

        project_root = pathlib.Path(__file__).resolve().parent.parent
        src_root = project_root / "corpus"
        src = src_root / "Background.md"
        dst = self.corpus_dir / src.relative_to(src_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._tmp.cleanup()
        os.environ.pop("RISKAGENT_CORPUS_DIR", None)
        os.environ.pop("RISKAGENT_PERSIST_DIR", None)
        os.environ.pop("RISKAGENT_ARTIFACTS_DIR", None)
        os.environ.pop("RISKAGENT_API_KEY", None)

    def test_trace_saved_with_request_bundle(self) -> None:
        def _fake_llm_json(prompt: str, temperature: float = 0.0):
            p = str(prompt or "")
            if "Schema" in p and "\"query\"" in p:
                return {"query": "frtb"}
            if "Schema" in p and "\"sufficient\"" in p:
                return {"sufficient": True, "improved_query": "", "reason": "ok"}
            if "Schema" in p and "\"should_call_tool\"" in p:
                return {"should_call_tool": False, "args": {}, "reason": "not needed"}
            return {}

        def _fake_llm_text(prompt: str, temperature: float = 0.0):
            return "ok"

        headers = {"X-API-Key": "k"}
        with patch("riskagent_agenticrag.rag.agentic_primitives.call_llm_json", side_effect=_fake_llm_json), patch(
            "riskagent_agenticrag.rag.agentic_primitives.call_llm_text", side_effect=_fake_llm_text
        ), patch("riskagent_agenticrag.llm.generate.call_llm_text", side_effect=_fake_llm_text):
            r = self.client.post("/v1/ask", headers=headers, json={"question": "what is frtb"})
            self.assertEqual(r.status_code, 200)
            body = r.json()

        debug = body.get("debug") or {}
        bundle_dir = str(debug.get("artifact_bundle_dir") or "").strip()
        self.assertTrue(bundle_dir)
        trace_path = pathlib.Path(bundle_dir) / "trace.json"
        self.assertTrue(trace_path.exists())

        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(str(trace.get("request_id") or ""), str(body.get("request_id") or ""))
        self.assertTrue(str(trace.get("run_id") or "").strip())
        self.assertIsInstance(trace.get("nodes"), list)

        nodes = trace.get("nodes") or []
        found = False
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if n.get("name") != "retrieve_and_critique":
                continue
            result = n.get("result") or {}
            docs = result.get("docs") or []
            self.assertIsInstance(docs, list)
            self.assertLessEqual(len(docs), 8)
            if docs:
                d0 = docs[0]
                self.assertTrue(str(d0.get("chunk_id") or "").strip())
                self.assertTrue(str(d0.get("source") or "").strip())
                self.assertTrue(str(d0.get("snippet") or "").strip())
            found = True
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
