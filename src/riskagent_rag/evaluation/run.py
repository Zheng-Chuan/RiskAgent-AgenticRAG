"""Evaluation runner.

中文注释
- 离线评测入口
- 当前只实现 citations coverage
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from riskagent_rag.evaluation.citations import compute_citations_coverage, is_valid_citation
from riskagent_rag.evaluation.citation_precision import try_compute_citation_precision
from riskagent_rag.evaluation.dataset import load_dataset
from riskagent_rag.evaluation.domain_consistency import try_compute_domain_consistency
from riskagent_rag.evaluation.ragas_integration import try_compute_ragas_metrics
from riskagent_rag.evaluation.reporting import compare_reports, find_latest_report, load_report, write_report
from riskagent_rag.indexing.indexer import incremental_index
from riskagent_rag.orchestration.langgraph_runner import run_langgraph_agentic_chat
from riskagent_rag.rag.pipeline import extract_citations
from riskagent_rag.rag.retriever_factory import build_retriever


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _stage_plan(stage: str) -> dict[str, Any]:
    stage = str(stage or "").lower().strip()
    plans: dict[str, dict[str, Any]] = {
        "step1": {
            "title": "step1 retrieval rerank and hybrid",
            "done": [
                "cross encoder reranking",
                "hybrid search bm25 and vector",
            ],
            "todo": [
                "query expansion and step back prompting",
                "sub question decomposition and semantic router",
                "advanced indexing parent child summary hyde",
                "self rag grading and adaptive retrieval",
            ],
        },
        "step2": {
            "title": "step2 query intelligence and routing",
            "done": [
                "query expansion",
                "step back prompting",
                "sub question decomposition",
                "semantic router",
            ],
            "todo": [
                "advanced indexing parent child summary hyde",
                "self rag grading and adaptive retrieval",
            ],
        },
        "step3": {
            "title": "step3 advanced indexing",
            "done": [
                "parent child indexing small to big",
                "summary indexing",
                "hyde indexing",
            ],
            "todo": [
                "self rag grading and adaptive retrieval",
            ],
        },
        "step4": {
            "title": "step4 self rag",
            "done": [
                "adaptive retrieval",
                "self reflection scoring isrel issup isuse",
                "grade docs and grade generation loop",
            ],
            "todo": [],
        },
    }
    if stage in plans:
        return {"stage": stage, **plans[stage]}
    if stage:
        return {"stage": stage, "title": stage, "done": [], "todo": []}
    return {}


def run_evaluation(*, corpus_dir: Path, dataset_path: Path, persist_dir: Path, enable_ragas: bool) -> dict[str, Any]:
    os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

    items = load_dataset(dataset_path)

    incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=None)
    retriever = build_retriever(persist_dir=persist_dir, final_k=4)

    samples: list[dict[str, Any]] = []
    for item in items:
        qid = str(item.item_id)
        question = str(item.question)
        out = run_langgraph_agentic_chat(question=question, retriever=retriever)
        answer = str(out.get("answer", ""))
        docs = out.get("docs", [])
        citations = out.get("citations")
        if not isinstance(citations, list):
            citations = extract_citations(docs)

        contexts: list[str] = []
        for d in docs[:4]:
            text = getattr(d, "page_content", "")
            contexts.append(str(text)[:500])

        valid = [c for c in citations if isinstance(c, dict) and is_valid_citation(c)]
        samples.append(
            {
                "id": qid,
                "question": question,
                "reference_answer": item.reference_answer,
                "ground_truth_contexts": item.ground_truth_contexts,
                "answer": answer,
                "answer_len": len(answer),
                "citation_count": len(citations),
                "valid_citation_count": len(valid),
                "passed": bool(answer.strip()) and bool(valid),
                "citations": citations,
                "contexts": contexts,
            }
        )

    cov = compute_citations_coverage(samples)
    ragas_result = None
    if enable_ragas:
        out = try_compute_ragas_metrics(samples=samples)
        ragas_result = {
            "enabled": out.enabled,
            "ok": out.ok,
            "metrics": out.metrics,
            "error": out.error,
        }
    enable_citation_judge = os.getenv("EVAL_ENABLE_CITATION_JUDGE", "").lower().strip() in {
        "true",
        "1",
        "yes",
    }
    citation_judge_mode = os.getenv("EVAL_CITATION_JUDGE_MODE", "auto").lower().strip() or "auto"
    citation_judge = None
    if enable_citation_judge:
        out = try_compute_citation_precision(samples=samples, mode=citation_judge_mode)
        citation_judge = {
            "enabled": out.enabled,
            "ok": out.ok,
            "metrics": out.metrics,
            "error": out.error,
            "details": out.details,
        }

    try:
        numeric_tolerance = float(os.getenv("EVAL_NUMERIC_TOLERANCE", "0.01"))
    except (TypeError, ValueError):
        numeric_tolerance = 0.01
    out = try_compute_domain_consistency(samples=samples, tolerance=numeric_tolerance)
    domain_consistency = {
        "enabled": out.enabled,
        "ok": out.ok,
        "metrics": out.metrics,
        "error": out.error,
        "details": out.details,
    }

    report: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "inputs": {
            "corpus_dir": str(corpus_dir),
            "dataset_path": str(dataset_path),
            "persist_dir": str(persist_dir),
            "k": 4,
            "milvus_uri": os.getenv("MILVUS_URI"),
            "milvus_host": os.getenv("MILVUS_HOST"),
            "milvus_port": os.getenv("MILVUS_PORT"),
            "retriever_mode": os.getenv("RISKAGENT_RETRIEVER_MODE", "step4"),
            "reranker_model": os.getenv("RISKAGENT_RERANKER_MODEL", ""),
        },
        "metrics": {
            "citations_total": cov.total,
            "citations_passed": cov.passed,
            "citations_coverage": cov.coverage,
        },
        "samples": samples,
    }

    if ragas_result is not None:
        report["ragas"] = ragas_result
    if citation_judge is not None:
        report["citation_judge"] = citation_judge
        if citation_judge.get("ok") and isinstance(citation_judge.get("metrics"), dict):
            try:
                report["metrics"]["citation_precision"] = float(citation_judge["metrics"].get("citation_precision", 0.0))
            except (TypeError, ValueError):
                pass
            try:
                report["metrics"]["hallucination_rate_in_citations"] = float(
                    citation_judge["metrics"].get("hallucination_rate_in_citations", 0.0)
                )
            except (TypeError, ValueError):
                pass

    report["domain_consistency"] = domain_consistency
    if domain_consistency.get("ok") and isinstance(domain_consistency.get("metrics"), dict):
        for k, v in domain_consistency["metrics"].items():
            try:
                report["metrics"][k] = float(v)
            except (TypeError, ValueError):
                pass

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--dataset", default="tests/data/questions.json")
    parser.add_argument("--persist-dir", default=".milvus")
    parser.add_argument("--artifacts-dir", default=".artifacts")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--stage", default="")
    parser.add_argument("--stage-notes", default="")
    parser.add_argument("--enable-ragas", action="store_true")
    parser.add_argument("--enable-citation-judge", action="store_true")
    parser.add_argument("--citation-judge-mode", default=os.getenv("EVAL_CITATION_JUDGE_MODE", "auto"))
    parser.add_argument("--numeric-tolerance", type=float, default=float(os.getenv("EVAL_NUMERIC_TOLERANCE", "0.01")))
    parser.add_argument("--tolerance", type=float, default=float(os.getenv("EVAL_TOLERANCE", "0")))
    parser.add_argument("--minimum", type=float, default=float(os.getenv("EVAL_MINIMUM", "0.8")))
    parser.add_argument(
        "--hallucination-maximum",
        type=float,
        default=float(os.getenv("EVAL_HALLUCINATION_MAXIMUM", "1.0")),
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    dataset_path = Path(args.dataset)
    persist_dir = Path(args.persist_dir)

    enable_ragas = bool(args.enable_ragas) or os.getenv("EVAL_ENABLE_RAGAS", "").lower().strip() in {
        "true",
        "1",
        "yes",
    }
    if str(args.stage).lower().strip() == "step1" and not os.getenv("RISKAGENT_RETRIEVER_MODE"):
        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step1"
    if str(args.stage).lower().strip() == "step2" and not os.getenv("RISKAGENT_RETRIEVER_MODE"):
        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step2"
    if str(args.stage).lower().strip() == "step3" and not os.getenv("RISKAGENT_RETRIEVER_MODE"):
        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step3"
    if str(args.stage).lower().strip() == "step4" and not os.getenv("RISKAGENT_RETRIEVER_MODE"):
        os.environ["RISKAGENT_RETRIEVER_MODE"] = "step4"
    if str(args.stage).lower().strip() in {"step1", "step2", "step3", "step4"} and not os.getenv("RISKAGENT_RERANKER_MODEL"):
        os.environ["RISKAGENT_RERANKER_MODEL"] = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    if bool(args.enable_citation_judge):
        os.environ["EVAL_ENABLE_CITATION_JUDGE"] = "true"
        os.environ["EVAL_CITATION_JUDGE_MODE"] = str(args.citation_judge_mode).lower().strip() or "auto"
    os.environ["EVAL_NUMERIC_TOLERANCE"] = str(float(args.numeric_tolerance))

    report = run_evaluation(
        corpus_dir=corpus_dir,
        dataset_path=dataset_path,
        persist_dir=persist_dir,
        enable_ragas=enable_ragas,
    )
    if args.stage or args.stage_notes:
        report["stage"] = {
            **_stage_plan(str(args.stage)),
            "notes": str(args.stage_notes).strip(),
        }

    baseline_path = args.baseline or find_latest_report(artifacts_dir=args.artifacts_dir)
    if baseline_path:
        baseline_report = load_report(baseline_path)
        diff = compare_reports(
            current_report=report,
            baseline_report=baseline_report,
            tolerance=args.tolerance,
            minimum=args.minimum,
            hallucination_maximum=args.hallucination_maximum,
        )
        report["baseline"] = {
            "path": baseline_path,
            "diff": diff,
        }

    label = str(args.label).strip()
    if not label and args.stage:
        label = str(args.stage).strip()
    out_path = write_report(report, artifacts_dir=args.artifacts_dir, label=label)
    print(out_path)


if __name__ == "__main__":
    main()
