"""Evaluation runner.

中文注释
- 离线评测入口
- 当前只实现 citations coverage
"""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from riskagent_rag.evaluation.citations import compute_citations_coverage, is_valid_citation
from riskagent_rag.evaluation.citation_precision import try_compute_citation_precision
from riskagent_rag.evaluation.dataset import load_dataset
from riskagent_rag.evaluation.ragas_integration import try_compute_ragas_metrics
from riskagent_rag.evaluation.reporting import compare_reports, find_latest_report, load_report, write_report
from riskagent_rag.graph.workflow import build_rag_graph
from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def run_evaluation(*, corpus_dir: Path, dataset_path: Path, enable_ragas: bool) -> dict[str, Any]:
    os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")
    # 不要强制 fallback, 允许外部通过环境变量注入 (e.g. LLM_PROVIDER=openai_compatible)
    # os.environ.setdefault("LLM_PROVIDER", "fallback")

    items = load_dataset(dataset_path)

    with tempfile.TemporaryDirectory() as td:
        persist_dir = Path(td) / "milvus"
        build_index(sources_dir=corpus_dir, persist_dir=persist_dir)
        vectorstore = load_index(persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        graph = build_rag_graph(retriever)

        samples: list[dict[str, Any]] = []
        for item in items:
            qid = str(item.item_id)
            question = str(item.question)
            out = graph.invoke({"question": question})
            answer = str(out.get("answer", ""))
            docs = out.get("docs", [])
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
        report: dict[str, Any] = {
            "generated_at": _utc_now_iso(),
            "inputs": {
                "corpus_dir": str(corpus_dir),
                "dataset_path": str(dataset_path),
                "k": 4,
                "milvus_host": os.getenv("MILVUS_HOST"),
                "milvus_port": os.getenv("MILVUS_PORT"),
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

        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--dataset", default="tests/data/questions.json")
    parser.add_argument("--artifacts-dir", default=".artifacts")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--enable-ragas", action="store_true")
    parser.add_argument("--enable-citation-judge", action="store_true")
    parser.add_argument("--citation-judge-mode", default=os.getenv("EVAL_CITATION_JUDGE_MODE", "auto"))
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

    enable_ragas = bool(args.enable_ragas) or os.getenv("EVAL_ENABLE_RAGAS", "").lower().strip() in {
        "true",
        "1",
        "yes",
    }
    if bool(args.enable_citation_judge):
        os.environ["EVAL_ENABLE_CITATION_JUDGE"] = "true"
        os.environ["EVAL_CITATION_JUDGE_MODE"] = str(args.citation_judge_mode).lower().strip() or "auto"

    report = run_evaluation(corpus_dir=corpus_dir, dataset_path=dataset_path, enable_ragas=enable_ragas)

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

    out_path = write_report(report, artifacts_dir=args.artifacts_dir)
    print(out_path)


if __name__ == "__main__":
    main()
