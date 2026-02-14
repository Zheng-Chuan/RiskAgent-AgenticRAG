from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from riskagent_rag.api.server import app
from riskagent_rag.indexing.indexer import incremental_index


class TestWeek12ApiV1Acceptance(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")
        os.environ["OPENAI_API_KEY"] = "test_key"
        os.environ.pop("LLM_API_KEY", None)
        os.environ.setdefault("LLM_MODEL", "test_model")
        os.environ.setdefault("LLM_BASE_URL", "http://example.invalid")
        os.environ.setdefault("RISKAGENT_API_KEY", "k")

        self._tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = pathlib.Path(self._tmp.name) / "corpus"
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        os.environ["RISKAGENT_CORPUS_DIR"] = str(self.corpus_dir)
        os.environ["RISKAGENT_PERSIST_DIR"] = str(self.persist_dir)

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
        os.environ.pop("RISKAGENT_API_KEY", None)

    def test_healthz_readyz_metrics(self) -> None:
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

        r = self.client.get("/readyz")
        self.assertIn(r.status_code, (200, 503))
        body = r.json()
        self.assertIn(body.get("status"), ("ready", "not_ready"))
        self.assertIn("details", body)

        r = self.client.get("/metrics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("riskagent_http_requests_total", r.text)

    def test_v1_ask_requires_api_key(self) -> None:
        r = self.client.post("/v1/ask", json={"question": "what is frtb"})
        self.assertEqual(r.status_code, 401)
        body = r.json()
        self.assertEqual(body.get("status"), "error")
        self.assertEqual((body.get("error") or {}).get("error_code"), "unauthorized")

    def test_v1_ask_schema_and_stability(self) -> None:
        def _fake_llm_json(prompt: str, temperature: float = 0.0):
            p = str(prompt or "")
            if "Schema" in p and "\"query\"" in p:
                return {"query": "frtb definition"}
            if "Schema" in p and "\"sufficient\"" in p:
                return {"sufficient": True, "improved_query": "", "reason": "ok"}
            if "Schema" in p and "\"should_call_tool\"" in p:
                return {"should_call_tool": False, "args": {}, "reason": "not needed"}
            return {}

        def _fake_llm_text(prompt: str, temperature: float = 0.0):
            return "FRTB is a market risk capital framework"

        headers = {"X-API-Key": "k"}
        with patch("riskagent_rag.rag.agentic_primitives.call_llm_json", side_effect=_fake_llm_json), patch(
            "riskagent_rag.rag.agentic_primitives.call_llm_text", side_effect=_fake_llm_text
        ), patch("riskagent_rag.llm.generate.call_llm_text", side_effect=_fake_llm_text):
            r = self.client.post("/v1/ask", headers=headers, json={"question": "what is frtb", "max_rounds": 2})
            self.assertEqual(r.status_code, 200)
            body = r.json()
            for k in (
                "request_id",
                "status",
                "answer",
                "citations",
                "claims",
                "evidence_set",
                "decision_log",
                "tool_traces",
                "failure_reason",
                "debug",
                "error",
            ):
                self.assertIn(k, body)

            self.assertTrue(str(body.get("request_id") or "").strip())
            self.assertIn(body.get("status"), ("ok", "failed", "error"))

            for _ in range(50):
                r2 = self.client.post("/v1/ask", headers=headers, json={"question": "what is frtb"})
                self.assertIn(r2.status_code, (200, 500))
                b2 = r2.json()
                self.assertIn("request_id", b2)

    def test_v1_chat(self) -> None:
        def _fake_llm_json(prompt: str, temperature: float = 0.0):
            p = str(prompt or "")
            if "Schema" in p and "\"query\"" in p:
                return {"query": "frtb basel"}
            if "Schema" in p and "\"sufficient\"" in p:
                return {"sufficient": True, "improved_query": "", "reason": "ok"}
            if "Schema" in p and "\"should_call_tool\"" in p:
                return {"should_call_tool": False, "args": {}, "reason": "not needed"}
            return {}

        def _fake_llm_text(prompt: str, temperature: float = 0.0):
            return "ok"

        headers = {"X-API-Key": "k"}
        with patch("riskagent_rag.rag.agentic_primitives.call_llm_json", side_effect=_fake_llm_json), patch(
            "riskagent_rag.rag.agentic_primitives.call_llm_text", side_effect=_fake_llm_text
        ), patch("riskagent_rag.llm.generate.call_llm_text", side_effect=_fake_llm_text):
            r = self.client.post(
                "/v1/chat",
                headers=headers,
                json={
                    "messages": [
                        {"role": "user", "content": "what is frtb"},
                        {"role": "assistant", "content": "ok"},
                        {"role": "user", "content": "how is it related to basel"},
                    ]
                },
            )
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertTrue(str(body.get("request_id") or "").strip())


if __name__ == "__main__":
    unittest.main()

