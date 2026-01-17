from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from tests.conftest import ensure_src_on_path


class Week5RefusalQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_src_on_path()

    def setUp(self) -> None:
        os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

        use_docker_milvus = os.getenv("RISKAGENT_USE_DOCKER_MILVUS", "").lower().strip() in ("true", "1", "yes")
        if not use_docker_milvus:
            os.environ.pop("MILVUS_URI", None)
            os.environ.pop("MILVUS_HOST", None)
            os.environ.pop("MILVUS_PORT", None)
            os.environ["MILVUS_WAIT_READY"] = "false"

        self.project_root = pathlib.Path(__file__).resolve().parent.parent
        self.sources_dir = self.project_root / "corpus"
        self.dataset_path = self.project_root / "tests" / "data" / "week5_refusal_set.json"
        self._tmp = tempfile.TemporaryDirectory()
        self.persist_dir = pathlib.Path(self._tmp.name) / "milvus"

        self.report_dir = self.project_root / "tests" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_refusal_quality_acceptance(self) -> None:
        from riskagent_rag.evaluation.refusal import compute_refusal_metrics, is_refusal_answer
        from riskagent_rag.rag.agentic_loop import run_agentic_chat
        from riskagent_rag.rag.pipeline import build_index, load_index

        items = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 10)

        build_index(sources_dir=self.sources_dir, persist_dir=self.persist_dir)
        vectorstore = load_index(self.persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

        rows: list[dict] = []
        samples: list[dict] = []

        for item in items:
            qid = str(item.get("id", ""))
            question = str(item.get("question", ""))
            expected_refuse = bool(item.get("expected_refuse", False))

            out = run_agentic_chat(question=question, retriever=retriever, max_rounds=2)
            answer = str(out.get("answer", ""))
            citations = out.get("citations", [])
            if not isinstance(citations, list):
                citations = []

            got_refuse = is_refusal_answer(answer=answer, citations=citations)

            if expected_refuse:
                self.assertTrue(got_refuse, f"id={qid} expected refuse")
            else:
                self.assertFalse(got_refuse, f"id={qid} unexpected refuse")
                self.assertTrue(answer.strip(), f"id={qid} empty answer")
                self.assertTrue(citations, f"id={qid} missing citations")

            rows.append(
                {
                    "id": qid,
                    "question": question,
                    "expected_refuse": expected_refuse,
                    "got_refuse": got_refuse,
                    "citation_count": len(citations),
                    "answer_preview": answer[:160],
                }
            )
            samples.append(
                {
                    "id": qid,
                    "expected_refuse": expected_refuse,
                    "got_refuse": got_refuse,
                }
            )

        metrics = compute_refusal_metrics(samples=samples)

        report = {
            "test_name": "test_refusal_quality_acceptance",
            "thresholds": {
                "false_refusal_rate_max": 0.05,
                "true_refusal_rate_min": 0.95,
            },
            "metrics": {
                "positive_total": metrics.positive_total,
                "negative_total": metrics.negative_total,
                "false_refusals": metrics.false_refusals,
                "true_refusals": metrics.true_refusals,
                "false_refusal_rate": metrics.false_refusal_rate,
                "true_refusal_rate": metrics.true_refusal_rate,
            },
            "results": rows,
        }

        out_path = self.report_dir / "week5_refusal_quality_report.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nWeek 5 Refusal Quality Report saved to: {out_path}")

        self.assertLess(metrics.false_refusal_rate, 0.05)
        self.assertGreater(metrics.true_refusal_rate, 0.95)

