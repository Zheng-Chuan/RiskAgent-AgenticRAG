from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document


def test_sample_contexts_prefer_expanded_text_for_evaluation() -> None:
    from riskagent_agenticrag.evaluation.run import _sample_contexts

    docs = [
        Document(
            page_content="short page content",
            metadata={
                "expanded_text": "expanded evidence block with more supporting detail",
            },
        )
    ]

    contexts = _sample_contexts(docs)

    assert contexts == ["expanded evidence block with more supporting detail"]


def test_sample_contexts_use_page_content_when_expanded_text_missing() -> None:
    from riskagent_agenticrag.evaluation.run import _sample_contexts

    docs = [Document(page_content="plain page content", metadata={})]

    contexts = _sample_contexts(docs)

    assert contexts == ["plain page content"]


def test_run_evaluation_uses_max_retrieval_k_for_final_k() -> None:
    from riskagent_agenticrag.evaluation.run import run_evaluation

    class _Item:
        item_id = "q01"
        question = "What is FRTB"
        reference_answer = "FRTB stands for Fundamental Review of the Trading Book."
        ground_truth_contexts = ["FRTB stands for Fundamental Review of the Trading Book."]
        reference_contexts = None
        tags = ["definition"]
        qrels = []
        gate_label = None

    captured: dict[str, int] = {}

    def _fake_build_retriever(*, persist_dir: Path, final_k: int):
        captured["final_k"] = int(final_k)
        return object()

    with (
        patch("riskagent_agenticrag.evaluation.run.load_dataset", return_value=[_Item()]),
        patch("riskagent_agenticrag.evaluation.run.incremental_index"),
        patch("riskagent_agenticrag.evaluation.run.build_retriever", side_effect=_fake_build_retriever),
        patch(
            "riskagent_agenticrag.evaluation.run.run_langgraph_agentic_chat",
            return_value={"answer": "ok", "docs": [], "citations": [], "status": "ok"},
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.compute_citations_coverage",
            return_value=type("Cov", (), {"total": 1, "passed": 0, "coverage": 0.0})(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.try_compute_citation_precision",
            return_value=type(
                "Cp",
                (),
                {"enabled": True, "ok": True, "metrics": {}, "details": [], "error": None},
            )(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.try_compute_domain_consistency",
            return_value=type(
                "Dc",
                (),
                {"enabled": True, "ok": True, "metrics": {}, "details": {"samples": []}, "error": None},
            )(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.build_answer_eval",
            return_value=type(
                "Ae",
                (),
                {"enabled": True, "ok": True, "metrics": {}, "thresholds": {}, "details": [], "error": None},
            )(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.compute_retrieval_metrics",
            return_value=type(
                "Rm",
                (),
                {
                    "enabled": True,
                    "ok": True,
                    "metrics": {"retrieval_recall_at_5": 1.0},
                    "error": None,
                    "gold_metrics": {},
                    "slice_metrics": {},
                },
            )(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.compute_gate_metrics",
            return_value=type(
                "Gm",
                (),
                {"enabled": True, "ok": True, "metrics": {}, "distributions": {}, "error": None},
            )(),
        ),
        patch(
            "riskagent_agenticrag.evaluation.run.compute_reliability_cost_metrics",
            return_value=type(
                "Rc",
                (),
                {"enabled": True, "ok": True, "metrics": {}, "node_latency_p95": {}, "error": None},
            )(),
        ),
    ):
        report = run_evaluation(
            corpus_dir=Path("corpus"),
            dataset_path=Path("tests/data/questions.json"),
            persist_dir=Path(".milvus"),
            enable_ragas=False,
            profile="all",
            retrieval_ks=[1, 3, 5],
            include_cost=False,
            include_latency=False,
            with_gate=True,
        )

    assert captured["final_k"] == 5
    assert report["inputs"]["k"] == 5
