from __future__ import annotations

import json
import os
import time
import unittest


class Week6CitationPrecisionQualityTest(unittest.TestCase):
    def test_heuristic_citation_precision(self) -> None:
        from riskagent_agenticrag.evaluation.citation_precision import (
            try_compute_citation_precision,
        )

        os.environ["EVAL_CITATION_JUDGE_MODE"] = "heuristic"

        samples = [
            {
                "id": "s1",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            }
        ]

        out = try_compute_citation_precision(samples=samples, mode="heuristic")
        self.assertTrue(out.ok)
        self.assertGreaterEqual(float(out.metrics.get("citation_precision", 0.0)), 0.99)
        self.assertEqual(out.details[0]["unsupported_sentences"], [])

    def test_heuristic_hallucination_rate(self) -> None:
        from riskagent_agenticrag.evaluation.citation_precision import (
            try_compute_citation_precision,
        )

        os.environ["EVAL_CITATION_JUDGE_MODE"] = "heuristic"

        samples = [
            {
                "id": "supported",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            },
            {
                "id": "unsupported",
                "question": "What is FRTB?",
                "answer": "FRTB was published in 2099.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            },
        ]

        out = try_compute_citation_precision(samples=samples, mode="heuristic")
        self.assertTrue(out.ok)
        self.assertGreater(float(out.metrics.get("hallucination_rate_in_citations", 0.0)), 0.0)
        self.assertGreater(float(out.metrics.get("unsupported_sentence_rate", 0.0)), 0.0)
        unsupported = [row for row in out.details if row["id"] == "unsupported"][0]
        self.assertTrue(unsupported["unsupported_sentences"])

    def test_llm_mode_falls_back_to_heuristic_when_judge_output_is_invalid(self) -> None:
        from unittest.mock import MagicMock, patch

        from riskagent_agenticrag.evaluation.citation_precision import (
            try_compute_citation_precision,
        )

        samples = [
            {
                "id": "s1",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            }
        ]

        fake_judge = MagicMock(invoke=MagicMock(return_value="not-json"))
        with patch("riskagent_agenticrag.evaluation.citation_precision.get_judge_llm", return_value=fake_judge):
            out = try_compute_citation_precision(samples=samples, mode="llm")

        self.assertTrue(out.ok)
        self.assertGreaterEqual(float(out.metrics.get("citation_precision", 0.0)), 0.99)
        self.assertEqual(out.details[0]["mode"], "heuristic_fallback")

    def test_get_judge_llm_inherits_timeout_and_headers(self) -> None:
        from unittest.mock import patch

        from pydantic import SecretStr
        from riskagent_agenticrag.config.settings import get_settings, settings
        from riskagent_agenticrag.evaluation.judge_llm import get_judge_llm

        original_api_key = settings.llm.api_key
        original_base_url = settings.llm.base_url
        original_model = settings.llm.model
        original_referer = os.environ.get("OPENROUTER_SITE_URL")
        original_title = os.environ.get("OPENROUTER_APP_NAME")

        class _FakeChatOpenAI:
            def __init__(self, **kwargs) -> None:
                self.kwargs = kwargs

        try:
            settings.llm.api_key = SecretStr("secret")
            settings.llm.base_url = "https://example.com/v1"
            settings.llm.model = "test-model"
            os.environ["OPENROUTER_SITE_URL"] = "https://example.com"
            os.environ["OPENROUTER_APP_NAME"] = "RiskAgent"

            with patch("langchain_openai.ChatOpenAI", _FakeChatOpenAI):
                llm = get_judge_llm()

            timeout_total = float(get_settings().llm_governance.timeout_total)
            self.assertEqual(llm.kwargs["model"], "test-model")
            self.assertEqual(llm.kwargs["base_url"], "https://example.com/v1")
            self.assertEqual(llm.kwargs["temperature"], 0)
            self.assertEqual(llm.kwargs["timeout"], timeout_total)
            self.assertEqual(
                llm.kwargs["default_headers"],
                {
                    "HTTP-Referer": "https://example.com",
                    "X-Title": "RiskAgent",
                },
            )
        finally:
            settings.llm.api_key = original_api_key
            settings.llm.base_url = original_base_url
            settings.llm.model = original_model
            if original_referer is None:
                os.environ.pop("OPENROUTER_SITE_URL", None)
            else:
                os.environ["OPENROUTER_SITE_URL"] = original_referer
            if original_title is None:
                os.environ.pop("OPENROUTER_APP_NAME", None)
            else:
                os.environ["OPENROUTER_APP_NAME"] = original_title

    def test_llm_mode_uses_bounded_parallelism(self) -> None:
        from threading import Lock
        from unittest.mock import patch

        from riskagent_agenticrag.evaluation.citation_precision import (
            try_compute_citation_precision,
        )

        samples = [
            {
                "id": "s1",
                "question": "What is FRTB?",
                "answer": "FRTB stands for Fundamental Review of the Trading Book.",
                "contexts": ["FRTB stands for Fundamental Review of the Trading Book."],
            },
            {
                "id": "s2",
                "question": "What is SA CCR?",
                "answer": "SA CCR is the standardized approach for counterparty credit risk.",
                "contexts": ["SA CCR is the standardized approach for counterparty credit risk."],
            },
            {
                "id": "s3",
                "question": "What is CVA?",
                "answer": "CVA stands for credit valuation adjustment.",
                "contexts": ["CVA stands for credit valuation adjustment."],
            },
            {
                "id": "s4",
                "question": "What is XVA?",
                "answer": "XVA refers to valuation adjustments.",
                "contexts": ["XVA refers to valuation adjustments."],
            },
        ]

        lock = Lock()
        state = {"active": 0, "max_active": 0}

        class _FakeJudge:
            def invoke(self, prompt: str) -> str:
                assert "citation_precision_judge" in prompt
                with lock:
                    state["active"] += 1
                    state["max_active"] = max(state["max_active"], state["active"])
                try:
                    time.sleep(0.05)
                    return json.dumps(
                        {
                            "total_sentences": 1,
                            "supported_sentences": 1,
                            "citation_precision": 1.0,
                            "unsupported_sentences": [],
                        }
                    )
                finally:
                    with lock:
                        state["active"] -= 1

        original_concurrency = os.environ.get("EVAL_CITATION_JUDGE_MAX_CONCURRENCY")
        original_progress = os.environ.get("EVAL_CITATION_JUDGE_PROGRESS")
        try:
            os.environ["EVAL_CITATION_JUDGE_MAX_CONCURRENCY"] = "2"
            os.environ["EVAL_CITATION_JUDGE_PROGRESS"] = "false"
            with patch("riskagent_agenticrag.evaluation.citation_precision.get_judge_llm", side_effect=lambda: _FakeJudge()):
                out = try_compute_citation_precision(samples=samples, mode="llm")
        finally:
            if original_concurrency is None:
                os.environ.pop("EVAL_CITATION_JUDGE_MAX_CONCURRENCY", None)
            else:
                os.environ["EVAL_CITATION_JUDGE_MAX_CONCURRENCY"] = original_concurrency
            if original_progress is None:
                os.environ.pop("EVAL_CITATION_JUDGE_PROGRESS", None)
            else:
                os.environ["EVAL_CITATION_JUDGE_PROGRESS"] = original_progress

        self.assertTrue(out.ok)
        self.assertEqual([row["id"] for row in out.details], ["s1", "s2", "s3", "s4"])
        self.assertGreaterEqual(state["max_active"], 2)
        self.assertLessEqual(state["max_active"], 2)
