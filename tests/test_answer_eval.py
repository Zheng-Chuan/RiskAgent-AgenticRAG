from __future__ import annotations

import unittest

from riskagent_agenticrag.evaluation.answer_eval import build_answer_eval


class AnswerEvalTest(unittest.TestCase):
    def test_build_answer_eval_uses_sentence_support_and_heuristic_relevancy(self) -> None:
        result = build_answer_eval(
            samples=[
                {
                    "id": "s1",
                    "question": "what is frtb",
                    "answer": "FRTB is a Basel market risk framework.",
                    "reference_answer": "FRTB is a regulatory framework for market risk capital.",
                }
            ],
            citation_coverage=0.8,
            citation_precision_result={
                "ok": True,
                "metrics": {
                    "sentence_support_rate": 0.75,
                    "unsupported_sentence_rate": 0.25,
                },
                "details": [
                    {
                        "id": "s1",
                        "supported_sentences": ["FRTB is a Basel market risk framework"],
                        "unsupported_sentences": ["It was defined yesterday"],
                    }
                ],
            },
            ragas_result=None,
            thresholds={"citation_coverage": 0.8, "faithfulness": 0.75, "answer_relevancy": 0.7},
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.metrics["faithfulness"], 0.75)
        self.assertGreater(result.metrics["answer_relevancy"], 0.0)
        self.assertEqual(result.details["samples"][0]["id"], "s1")

    def test_build_answer_eval_uses_reference_answer_to_reduce_false_low_relevancy(self) -> None:
        result = build_answer_eval(
            samples=[
                {
                    "id": "s1",
                    "question": "Explain Delta in the context of derivatives risk.",
                    "answer": "Delta is the sensitivity of a derivative's value to the underlying price level.",
                    "reference_answer": "Delta is the sensitivity of a derivative's value to small changes in the underlying price level.",
                }
            ],
            citation_coverage=1.0,
            citation_precision_result={
                "ok": True,
                "metrics": {
                    "sentence_support_rate": 1.0,
                    "unsupported_sentence_rate": 0.0,
                },
                "details": [],
            },
            ragas_result=None,
            thresholds={"citation_coverage": 0.8, "faithfulness": 0.75, "answer_relevancy": 0.7},
        )
        self.assertGreaterEqual(result.metrics["answer_relevancy"], 0.7)


if __name__ == "__main__":
    unittest.main()
