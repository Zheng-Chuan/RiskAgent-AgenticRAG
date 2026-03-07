from __future__ import annotations

import json
import os
import pathlib
import shutil
import socket
import tempfile
import unittest
import uuid
from unittest.mock import patch

class TestIntegrationFRTBRealMiddlewareArtifact(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus_dir = pathlib.Path(self._tmp.name) / "corpus"
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"
        self.artifacts_dir = pathlib.Path(self._tmp.name) / "artifacts"
        self.request_id = f"it-frtb-{uuid.uuid4().hex[:12]}"
        self.collection_name = f"riskagent_it_{uuid.uuid4().hex[:12]}"

        project_root = pathlib.Path(__file__).resolve().parent.parent
        src_root = project_root / "corpus"
        candidates = [
            src_root / "regulatory_seed" / "md" / "en" / "wikipedia_frtb.md",
            src_root / "Background.md",
        ]
        for src in candidates:
            dst = self.corpus_dir / src.relative_to(src_root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

        self._env_backup = {k: os.environ.get(k) for k in self._env_keys()}
        os.environ["EMBEDDINGS_PROVIDER"] = "hf"
        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step4"
        os.environ["RISKAGENT_SELF_RAG"] = "true"
        os.environ["RISKAGENT_CORPUS_DIR"] = str(self.corpus_dir)
        os.environ["RISKAGENT_PERSIST_DIR"] = str(self.persist_dir)
        os.environ["RISKAGENT_ARTIFACTS_DIR"] = str(self.artifacts_dir)
        os.environ["MILVUS_HOST"] = "127.0.0.1"
        os.environ["MILVUS_PORT"] = "19530"
        os.environ["MILVUS_COLLECTION"] = self.collection_name

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            if sock.connect_ex(("127.0.0.1", 19530)) != 0:
                self.fail("Milvus docker middleware is not reachable at 127.0.0.1:19530")

        from riskagent_rag.indexing.indexer import incremental_index

        incremental_index(corpus_dir=self.corpus_dir, persist_dir=self.persist_dir, include_paths=None)

    def tearDown(self) -> None:
        for k, v in self._env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    @staticmethod
    def _env_keys() -> list[str]:
        return [
            "EMBEDDINGS_PROVIDER",
            "RISKAGENT_RETRIEVER_MODE",
            "RISKAGENT_SELF_RAG",
            "RISKAGENT_CORPUS_DIR",
            "RISKAGENT_PERSIST_DIR",
            "RISKAGENT_ARTIFACTS_DIR",
            "MILVUS_HOST",
            "MILVUS_PORT",
            "MILVUS_COLLECTION",
        ]

    def _fake_llm_json(self, prompt: str, temperature: float = 0.0) -> dict[str, object]:
        p = str(prompt or "")
        if "Schema" in p and "\"query\"" in p:
            return {"query": "what is frtb overview definition market risk framework"}
        if "Schema" in p and "\"sufficient\"" in p:
            return {"sufficient": True, "improved_query": "", "reason": "retrieved chunks are sufficient"}
        if "Schema" in p and "\"should_call_tool\"" in p:
            return {"should_call_tool": False, "args": {}, "reason": "definition question no desk tool needed"}
        return {}

    def _fake_llm_text(self, prompt: str, temperature: float = 0.0) -> str:
        return (
            "1) TLDR\n"
            "- FRTB is the Fundamental Review of the Trading Book.\n"
            "- It revises market risk capital rules under Basel.\n\n"
            "2) Concept\n"
            "FRTB is a regulatory framework for trading-book market risk.\n\n"
            "3) Why it matters\n"
            "It improves risk sensitivity and model governance.\n\n"
            "4) Data flow / fields\n"
            "Typical implementation uses desk level data and risk factor mapping.\n\n"
            "5) Example\n"
            "A trading desk with non modellable factors may face higher capital.\n\n"
            "6) Citations\n"
            "Citations are attached by the pipeline."
        )

    def test_frtb_full_flow_and_artifact_bundle_with_real_middleware(self) -> None:
        from riskagent_rag.app import RiskAgentSystem

        system = RiskAgentSystem()
        with patch("riskagent_rag.rag.agentic_primitives.call_llm_json", side_effect=self._fake_llm_json), patch(
            "riskagent_rag.llm.generate.call_llm_text", side_effect=self._fake_llm_text
        ):
            out = system.chat("what is FRTB", max_rounds=2, request_id=self.request_id)

        self.assertIn(str(out.get("status") or ""), {"ok", "failed"})
        self.assertEqual(self.request_id, out.get("request_id"))
        self.assertTrue(str(out.get("answer") or "").strip())
        self.assertIsInstance(out.get("citations"), list)
        self.assertIsInstance(out.get("claims"), list)
        self.assertIsInstance(out.get("evidence_set"), list)

        debug = out.get("debug") or {}
        bundle_dir = pathlib.Path(str(debug.get("artifact_bundle_dir") or ""))
        self.assertTrue(bundle_dir.exists())

        request_path = bundle_dir / "request.json"
        response_path = bundle_dir / "response.json"
        structured_path = bundle_dir / "structured_response.json"
        trace_path = bundle_dir / "trace.json"
        self.assertTrue(request_path.exists())
        self.assertTrue(response_path.exists())
        self.assertTrue(trace_path.exists())

        request_json = json.loads(request_path.read_text(encoding="utf-8"))
        response_json = json.loads(response_path.read_text(encoding="utf-8"))
        trace_json = json.loads(trace_path.read_text(encoding="utf-8"))

        self.assertEqual("what is FRTB", str(request_json.get("question") or ""))
        self.assertEqual(2, int(request_json.get("max_rounds")))
        self.assertIn(str(response_json.get("status") or ""), {"ok", "failed"})
        self.assertTrue(str(response_json.get("answer") or "").strip())
        self.assertIsInstance(response_json.get("citations"), list)
        self.assertIsInstance(response_json.get("claims"), list)
        self.assertIsInstance(response_json.get("evidence_set"), list)
        if structured_path.exists():
            structured_json = json.loads(structured_path.read_text(encoding="utf-8"))
            self.assertEqual(self.request_id, str(structured_json.get("request_id") or ""))
            self.assertIn(str(structured_json.get("status") or ""), {"ok", "failed"})
            self.assertIsInstance(structured_json.get("claims"), list)
            self.assertIsInstance(structured_json.get("evidence_set"), list)

        nodes = trace_json.get("nodes")
        self.assertIsInstance(nodes, list)
        names = [str(n.get("name")) for n in nodes if isinstance(n, dict)]
        self.assertIn("rewrite", names)
        self.assertIn("retrieve_and_critique", names)
        self.assertIn("synthesize_answer", names)
        self.assertIn("validate_and_save", names)

        retrieve_nodes = [n for n in nodes if isinstance(n, dict) and str(n.get("name")) == "retrieve_and_critique"]
        self.assertTrue(retrieve_nodes)
        result = retrieve_nodes[0].get("result") or {}
        docs = result.get("docs") or []
        self.assertIsInstance(docs, list)
        self.assertTrue(docs)
        first = docs[0]
        self.assertTrue(str(first.get("chunk_id") or "").strip())
        self.assertTrue(str(first.get("source") or "").strip())
        self.assertTrue(str(first.get("snippet") or "").strip())


if __name__ == "__main__":
    unittest.main()
