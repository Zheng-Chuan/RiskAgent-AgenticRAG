from __future__ import annotations

import json
import tempfile
import unittest
import importlib
from pathlib import Path

from tests.conftest import ensure_src_on_path

ensure_src_on_path()

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
            payload = [
                {
                    "id": "s1",
                    "question": "what is frtb",
                    "reference_answer": "x",
                    "ground_truth_contexts": ["c1", "c2"],
                }
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            items = load_dataset(path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].item_id, "s1")
            self.assertEqual(items[0].reference_answer, "x")
            self.assertEqual(items[0].ground_truth_contexts, ["c1", "c2"])


if __name__ == "__main__":
    unittest.main()
