from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

mod = importlib.import_module("riskagent_agenticrag.evaluation.baseline_long_context")


def _fake_parent(pid: str, text: str, source: str = "corpus/a.md") -> SimpleNamespace:
    return SimpleNamespace(page_content=text, metadata={"parent_id": pid, "source": source})


class PackParentsTest(unittest.TestCase):
    def test_packs_in_order_until_window_full(self) -> None:
        parents = {
            "p1": _fake_parent("p1", "A" * 100),
            "p2": _fake_parent("p2", "B" * 100),
            "p3": _fake_parent("p3", "C" * 100),
        }
        # 每个 parent 约 125 chars (含 source 头), 100 tokens = 400 chars 可容 3 个
        packed = mod.pack_parents(["p1", "p2", "p3"], parents, window_tokens=100)
        self.assertEqual(packed.used_parent_ids, ["p1", "p2", "p3"])
        self.assertFalse(packed.truncated)
        self.assertIn("AAA", packed.text)
        self.assertIn("BBB", packed.text)

    def test_truncates_when_window_exceeded(self) -> None:
        parents = {
            "p1": _fake_parent("p1", "A" * 400),
            "p2": _fake_parent("p2", "B" * 400),
        }
        packed = mod.pack_parents(["p1", "p2"], parents, window_tokens=128)
        self.assertEqual(packed.used_parent_ids, ["p1"])
        self.assertTrue(packed.truncated)

    def test_dedupes_and_skips_unknown(self) -> None:
        parents = {"p1": _fake_parent("p1", "A")}
        packed = mod.pack_parents(["p1", "p1", "missing"], parents, window_tokens=1000)
        self.assertEqual(packed.used_parent_ids, ["p1"])


class OrderedParentIdsTest(unittest.TestCase):
    def test_extracts_ordered_unique_parent_ids(self) -> None:
        docs = [
            SimpleNamespace(metadata={"parent_id": "p2"}),
            SimpleNamespace(metadata={"parent_id": "p1"}),
            SimpleNamespace(metadata={"parent_id": "p2"}),
            SimpleNamespace(metadata={}),
        ]
        self.assertEqual(mod.ordered_parent_ids_from_docs(docs), ["p2", "p1"])


class AggregateRunStatsTest(unittest.TestCase):
    def test_aggregates_latency_tokens_refusal(self) -> None:
        samples = [
            {"latency_ms": 100.0, "prompt_tokens": 10, "completion_tokens": 5, "refusal": False, "status": "ok"},
            {"latency_ms": 300.0, "prompt_tokens": 30, "completion_tokens": 10, "refusal": True, "status": "ok"},
        ]
        stats = mod.aggregate_run_stats(samples)
        self.assertEqual(stats["n"], 2.0)
        self.assertEqual(stats["refusal_rate"], 0.5)
        self.assertEqual(stats["prompt_tokens_mean"], 20.0)
        self.assertEqual(stats["total_tokens_mean"], 27.5)
        self.assertGreaterEqual(stats["latency_p95_ms"], stats["latency_p50_ms"])

    def test_error_rate_counts_error_status(self) -> None:
        samples = [
            {"latency_ms": 1.0, "status": "ok"},
            {"latency_ms": 1.0, "status": "error: boom"},
        ]
        stats = mod.aggregate_run_stats(samples)
        self.assertEqual(stats["error_rate"], 0.5)


class ParentStuffingRunnerTest(unittest.TestCase):
    def test_stuffs_window_and_answers(self) -> None:
        parents = {"p1": _fake_parent("p1", "Delta definition text", source="corpus/Background.md")}
        fake_retriever = SimpleNamespace(
            invoke=lambda q: [SimpleNamespace(metadata={"parent_id": "p1"})]
        )

        def fake_llm(prompt: str) -> str:
            self.assertIn("Delta definition text", prompt)
            return "Delta is a Greek."

        items = [SimpleNamespace(item_id="q1", question="What is delta?",
                                 reference_answer=None, reference_contexts=[])]
        samples = mod.run_parent_stuffing(
            items, retriever=fake_retriever, parents_by_id=parents, llm_call=fake_llm
        )
        s = samples[0]
        self.assertEqual(s["answer"], "Delta is a Greek.")
        self.assertEqual(s["used_parent_count"], 1)
        self.assertFalse(s["window_truncated"])
        self.assertTrue(s["contexts"])


class RenderMarkdownTest(unittest.TestCase):
    def test_renders_comparison_table(self) -> None:
        report = mod.build_comparison_report(
            {
                "rag_main": {
                    "metrics": {"faithfulness": 0.9, "numeric_consistency_score": 0.8},
                    "run_stats": {"latency_p50_ms": 100.0, "latency_p95_ms": 200.0,
                                  "prompt_tokens_mean": 1000.0, "completion_tokens_mean": 200.0,
                                  "total_tokens_mean": 1200.0},
                    "confidence_intervals": {"faithfulness": {"ci_low": 0.85, "ci_high": 0.95}},
                },
                "parent_stuffing": {
                    "metrics": {"faithfulness": 0.8},
                    "run_stats": {"latency_p50_ms": 500.0, "latency_p95_ms": 900.0,
                                  "prompt_tokens_mean": 50000.0, "completion_tokens_mean": 300.0,
                                  "total_tokens_mean": 50300.0},
                    "confidence_intervals": {},
                },
            },
            modes=["rag_main", "parent_stuffing"],
            meta={"dataset": "tests/data/questions.json", "n_questions": 2,
                  "window_tokens": 128000},
        )
        md = mod.render_markdown(report)
        self.assertIn("长上下文基线对比实验", md)
        self.assertIn("faithfulness", md)
        self.assertIn("95% CI 0.850-0.950", md)
        self.assertIn("parent_stuffing", md)
        self.assertIn("50,300", md)


class RunBaselineExperimentTest(unittest.TestCase):
    def test_orchestrates_modes_with_injected_deps_and_writes_report(self) -> None:
        fake_retriever = SimpleNamespace(
            invoke=lambda q: [SimpleNamespace(metadata={"parent_id": "p1"})]
        )
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d)
            report = mod.run_baseline_experiment(
                corpus_dir=Path("corpus"),
                dataset_path=Path("tests/data/questions.json"),
                persist_dir=Path(".milvus"),
                modes=["parent_stuffing"],
                limit=0,
                out_dir=out_dir,
                enable_ragas=False,
                llm_call=lambda prompt: "answer",
                retriever=fake_retriever,
            )
            # 注入的 parents 无法通过 persist_dir 加载, 这里只验证编排与落盘路径
            files = list(out_dir.glob("long_context_baseline_*.json"))
            self.assertEqual(len(files), 1)
            saved = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertIn("parent_stuffing", saved["results"])
            # samples 明细不进主报告
            self.assertNotIn("samples", saved["results"]["parent_stuffing"])
            self.assertTrue(list(out_dir.glob("long_context_baseline_*.md")))
            self.assertEqual(report["meta"]["n_questions"], 50)

    def test_unknown_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            mod.run_baseline_experiment(
                corpus_dir=Path("corpus"),
                dataset_path=Path("tests/data/questions.json"),
                persist_dir=Path(".milvus"),
                modes=["bogus_mode"],
            )


if __name__ == "__main__":
    unittest.main()
