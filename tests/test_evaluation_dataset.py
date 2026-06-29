from __future__ import annotations

import json
import tempfile
import unittest
import importlib
from pathlib import Path



load_dataset = importlib.import_module("riskagent_agenticrag.evaluation.dataset").load_dataset


class EvaluationDatasetTest(unittest.TestCase):
    def test_load_questions_json_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "questions.json"
            path.write_text(json.dumps([{"id": "q1", "question": "what is frtb"}]), encoding="utf-8")
            items = load_dataset(path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].item_id, "q1")
            self.assertEqual(items[0].question, "what is frtb")

    def test_load_eval_set_with_optional_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "eval_set.json"
            qrels_path = Path(td) / "qrels.json"
            gate_labels_path = Path(td) / "gate_labels.json"
            payload = [
                {
                    "id": "s1",
                    "question": "what is frtb",
                    "reference_answer": "x",
                    "ground_truth_contexts": ["c1", "c2"],
                    "tags": ["definition", "regulation"],
                }
            ]
            qrels = [
                {
                    "id": "s1",
                    "qrels": [
                        {"qrel_id": "s1_r1", "text": "c1", "chunk_id": "chunk-1", "source": "corpus/a.md", "relevance": 2},
                        {"qrel_id": "s1_r2", "text": "c2", "section_path": "sec/b", "parent_id": "parent-2", "relevance": 1},
                    ],
                }
            ]
            gate_labels = [
                {
                    "id": "s1",
                    "should_block": False,
                    "label_source": "manual",
                    "reason": "should answer",
                }
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            qrels_path.write_text(json.dumps(qrels), encoding="utf-8")
            gate_labels_path.write_text(json.dumps(gate_labels), encoding="utf-8")
            items = load_dataset(path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].item_id, "s1")
            self.assertEqual(items[0].reference_answer, "x")
            self.assertEqual(items[0].ground_truth_contexts, ["c1", "c2"])
            self.assertEqual(items[0].tags, ["definition", "regulation"])
            self.assertEqual(len(items[0].qrels), 2)
            self.assertEqual(items[0].qrels[0].qrel_id, "s1_r1")
            self.assertEqual(items[0].qrels[0].relevance, 2)
            self.assertEqual(items[0].qrels[0].chunk_id, "chunk-1")
            self.assertEqual(items[0].qrels[0].source, "corpus/a.md")
            self.assertEqual(items[0].qrels[1].section_path, "sec/b")
            self.assertEqual(items[0].qrels[1].parent_id, "parent-2")
            self.assertFalse(items[0].gate_label.should_block)

    def test_reject_text_only_qrel_without_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "questions.json"
            qrels_path = Path(td) / "qrels.json"
            path.write_text(json.dumps([{"id": "q1", "question": "what is theta"}]), encoding="utf-8")
            qrels_path.write_text(
                json.dumps([{"id": "q1", "qrels": [{"qrel_id": "q1_r1", "text": "theta definition", "relevance": 2}]}]),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "qrels_gap_allowlist"):
                load_dataset(path)

    def test_accept_text_only_qrel_with_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "questions.json"
            qrels_path = Path(td) / "qrels.json"
            allowlist_path = Path(td) / "qrels_gap_allowlist.json"
            path.write_text(json.dumps([{"id": "q1", "question": "what is theta"}]), encoding="utf-8")
            qrels_path.write_text(
                json.dumps([{"id": "q1", "qrels": [{"qrel_id": "q1_r1", "text": "theta definition", "relevance": 2}]}]),
                encoding="utf-8",
            )
            allowlist_path.write_text(
                json.dumps([{"id": "q1", "reason": "approved_gap"}]),
                encoding="utf-8",
            )
            items = load_dataset(path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].qrels[0].text, "theta definition")


if __name__ == "__main__":
    unittest.main()
