from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from riskagent_agenticrag.evaluation.advanced_metrics import compute_retrieval_metrics
from riskagent_agenticrag.evaluation.dataset import load_dataset


class ContractMilestone2AcceptanceTest(unittest.TestCase):
    def test_dataset_loads_qrels_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset_path = Path(td) / "questions.json"
            qrels_path = Path(td) / "qrels.json"
            dataset_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "q1",
                            "question": "what is frtb",
                            "reference_answer": "x",
                            "ground_truth_contexts": ["ctx-1"],
                            "tags": ["definition", "regulation"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            qrels_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "q1",
                            "qrels": [{"qrel_id": "q1_r1", "text": "ctx-1", "chunk_id": "ctx-1-chunk", "source": "corpus/a.md", "relevance": 2}],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            items = load_dataset(dataset_path)
        self.assertEqual(items[0].tags, ["definition", "regulation"])
        self.assertEqual(items[0].qrels[0].qrel_id, "q1_r1")
        self.assertEqual(items[0].qrels[0].chunk_id, "ctx-1-chunk")

    def test_retrieval_metrics_use_qrels_and_emit_slice_metrics(self) -> None:
        samples = [
            {
                "tags": ["definition"],
                "qrels": [{"qrel_id": "q1_r1", "text": "frtb definition", "relevance": 2}],
                "retrieved_docs": [
                    {"source": "corpus/a.md", "chunk_id": "a1", "content": "frtb definition", "dense_rank": 1},
                ],
            },
            {
                "tags": ["compare"],
                "qrels": [{"qrel_id": "q2_r1", "text": "gamma delta difference", "relevance": 2}],
                "retrieved_docs": [
                    {"source": "corpus/b.md", "chunk_id": "b1", "content": "other", "dense_rank": 1},
                ],
            },
        ]
        out = compute_retrieval_metrics(samples=samples, ks=[1, 5])
        self.assertIn("retrieval_recall_at_1", out.metrics)
        self.assertIn("definition", out.slice_metrics)
        self.assertIn("compare", out.slice_metrics)
        self.assertEqual(out.slice_metrics["definition"]["retrieval_recall_at_1"], 1.0)
        self.assertEqual(out.slice_metrics["compare"]["retrieval_recall_at_1"], 0.0)


if __name__ == "__main__":
    unittest.main()
