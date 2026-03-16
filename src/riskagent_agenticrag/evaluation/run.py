"""Evaluation runner.

中文注释
- 离线评测入口
- 当前只实现 citations coverage
"""

from __future__ import annotations

import os

# Force offline mode BEFORE any HuggingFace imports
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from riskagent_agenticrag.evaluation.advanced_metrics import (
    compute_gate_metrics,
    compute_reliability_cost_metrics,
    compute_retrieval_metrics,
)
from riskagent_agenticrag.evaluation.citations import compute_citations_coverage, is_valid_citation
from riskagent_agenticrag.evaluation.dataset import load_dataset
from riskagent_agenticrag.evaluation.domain_consistency import try_compute_domain_consistency
from riskagent_agenticrag.evaluation.ragas_metrics import compute_all_ragas_metrics, get_all_metrics_description
from riskagent_agenticrag.evaluation.report_generator import generate_markdown_report, generate_comparison_report
from riskagent_agenticrag.evaluation.reporting import compare_reports, find_latest_report, load_report, write_report
from riskagent_agenticrag.evaluation.thresholds import evaluate_threshold_gate, load_thresholds
from riskagent_agenticrag.indexing.indexer import incremental_index
from riskagent_agenticrag.orchestration.langgraph_runner import run_langgraph_agentic_chat
from riskagent_agenticrag.rag.pipeline import extract_citations
from riskagent_agenticrag.rag.retriever_factory import build_retriever


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


def _doc_eval_row(doc: Any) -> dict[str, Any]:
    meta = getattr(doc, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "chunk_id": str(meta.get("chunk_id") or ""),
        "source": str(meta.get("source") or ""),
        "section_path": str(meta.get("section_path") or ""),
        "dense_rank": meta.get("dense_rank"),
        "sparse_rank": meta.get("sparse_rank"),
        "rrf_score": meta.get("rrf_score"),
        "coarse_score": meta.get("coarse_score"),
        "rerank_score": meta.get("rerank_score"),
    }


def _load_node_latencies(debug: dict[str, Any]) -> dict[str, float]:
    bundle_dir = str(debug.get("artifact_bundle_dir") or "").strip()
    if not bundle_dir:
        return {}
    path = Path(bundle_dir) / "trace.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return {}
    out: dict[str, float] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "").strip()
        if not name:
            continue
        try:
            latency_ms = float(node.get("latency_ms"))
        except (TypeError, ValueError):
            continue
        prev = out.get(name)
        out[name] = max(float(prev), latency_ms) if prev is not None else latency_ms
    return out


def _parse_retrieval_ks(text: str) -> list[int]:
    values: list[int] = []
    for part in str(text or "").split(","):
        raw = part.strip()
        if not raw:
            continue
        try:
            v = int(raw)
        except ValueError:
            continue
        if v > 0:
            values.append(v)
    if not values:
        return [1, 3, 5]
    return sorted(set(values))


def _profile_flags(profile: str) -> dict[str, bool]:
    p = str(profile or "all").lower().strip()
    if p == "retrieval":
        return {"retrieval": True, "gate": False, "reliability": False}
    if p == "gate":
        return {"retrieval": False, "gate": True, "reliability": False}
    if p == "reliability":
        return {"retrieval": False, "gate": False, "reliability": True}
    return {"retrieval": True, "gate": True, "reliability": True}


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").lower().strip() in {"true", "1", "yes"}


def _result_payload(out: Any) -> dict[str, Any]:
    return {
        "enabled": out.enabled,
        "ok": out.ok,
        "metrics": out.metrics,
        "error": out.error,
    }


def _merge_float_metrics(target: dict[str, Any], source: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        try:
            target[key] = float(source.get(key, 0.0))
        except (TypeError, ValueError):
            pass


def run_evaluation(
    *,
    corpus_dir: Path,
    dataset_path: Path,
    persist_dir: Path,
    enable_ragas: bool,
    profile: str,
    retrieval_ks: list[int],
    include_cost: bool,
    include_latency: bool,
    with_gate: bool,
) -> dict[str, Any]:
    os.environ.setdefault("EMBEDDINGS_PROVIDER", "hf")

    items = load_dataset(dataset_path)

    incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=None)
    retriever = build_retriever(persist_dir=persist_dir, final_k=4)

    samples: list[dict[str, Any]] = []
    for item in items:
        qid = str(item.item_id)
        question = str(item.question)
        t0 = time.perf_counter()
        out = run_langgraph_agentic_chat(question=question, retriever=retriever)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        answer = str(out.get("answer", ""))
        docs = out.get("docs", [])
        citations = out.get("citations")
        if not isinstance(citations, list):
            citations = extract_citations(docs)

        contexts: list[str] = []
        for d in docs[:4]:
            text = getattr(d, "page_content", "")
            contexts.append(str(text)[:500])
        retrieved_docs = [_doc_eval_row(d) for d in docs]

        debug = out.get("debug")
        if not isinstance(debug, dict):
            debug = {}
        node_latencies = _load_node_latencies(debug)

        valid = [c for c in citations if isinstance(c, dict) and is_valid_citation(c)]
        samples.append(
            {
                "id": qid,
                "question": question,
                "reference_answer": item.reference_answer,
                "ground_truth_contexts": item.ground_truth_contexts,
                "reference_contexts": item.reference_contexts,  # For RAGAS context_precision
                "answer": answer,
                "answer_len": len(answer),
                "citation_count": len(citations),
                "valid_citation_count": len(valid),
                "passed": bool(answer.strip()) and bool(valid),
                "citations": citations,
                "contexts": contexts,
                "retrieved_docs": retrieved_docs,
                "status": str(out.get("status") or ""),
                "failure_reason": out.get("failure_reason"),
                "latency_ms": latency_ms,
                "node_latencies": node_latencies,
                "decision_log": out.get("decision_log"),
                "tool_traces": out.get("tool_traces"),
            }
        )

    cov = compute_citations_coverage(samples)
    
    # RAGAS metrics - Full metrics evaluation
    ragas_result = None
    if enable_ragas:
        ragas_out = compute_all_ragas_metrics(
            samples=samples,
            include_reference_based=True,
            include_context_precision=True,
            include_low_priority=False,
        )
        ragas_result = {
            "enabled": ragas_out.enabled,
            "ok": ragas_out.ok,
            "metrics": ragas_out.metrics,
            "raw_scores": ragas_out.raw_scores,
            "error": ragas_out.error,
        }
        if not ragas_out.ok:
            print(f"Warning: RAGAS metrics failed: {ragas_out.error}", file=os.sys.stderr)

    # Domain consistency (financial-specific metrics)
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
            "profile": str(profile or "all"),
            "retrieval_ks": retrieval_ks,
            "include_cost": bool(include_cost),
            "include_latency": bool(include_latency),
            "with_gate": bool(with_gate),
            "enable_ragas": bool(enable_ragas),
        },
        "metrics": {
            "citations_total": cov.total,
            "citations_passed": cov.passed,
            "citations_coverage": cov.coverage,
        },
        "samples": samples,
    }

    # Merge RAGAS metrics into main metrics (RAGAS replaces citation_precision)
    if ragas_result is not None and ragas_result.get("ok"):
        report["ragas"] = ragas_result
        if isinstance(ragas_result.get("metrics"), dict):
            # Map RAGAS metrics to standard metric names for threshold checking
            ragas_metrics = ragas_result["metrics"]
            metric_mapping = {
                "ragas_faithfulness": "faithfulness",  # Primary replacement for citation_precision
                "ragas_answer_relevancy": "answer_relevancy",
                "ragas_context_precision": "context_precision",
                "ragas_context_recall": "context_recall",
                "ragas_answer_correctness": "answer_correctness",
                "ragas_factual_correctness": "factual_correctness",
                "ragas_context_precision_no_ref": "context_precision_no_ref",
                "ragas_contradiction_score": "contradiction_score",
            }
            for ragas_key, standard_key in metric_mapping.items():
                if ragas_key in ragas_metrics:
                    report["metrics"][standard_key] = float(ragas_metrics[ragas_key])
            # Also keep original RAGAS names
            report["metrics"].update(ragas_metrics)
    elif ragas_result is not None:
        report["ragas"] = ragas_result  # Keep error info

    # Domain consistency metrics
    report["domain_consistency"] = domain_consistency
    if domain_consistency.get("ok") and isinstance(domain_consistency.get("metrics"), dict):
        for k, v in domain_consistency["metrics"].items():
            try:
                report["metrics"][k] = float(v)
            except (TypeError, ValueError):
                pass

    flags = _profile_flags(profile)
    if bool(with_gate):
        flags["gate"] = True
    if flags["retrieval"]:
        retrieval = compute_retrieval_metrics(samples=samples, ks=retrieval_ks)
        report["retrieval_metrics"] = retrieval.metrics
        report["metrics"].update(retrieval.metrics)
    if flags["gate"]:
        gate = compute_gate_metrics(samples=samples)
        report["gate_metrics"] = {
            "metrics": gate.metrics,
            "distributions": gate.distributions,
        }
        report["metrics"].update(gate.metrics)
    if flags["reliability"]:
        rc = compute_reliability_cost_metrics(
            samples=samples,
            include_latency=bool(include_latency),
            include_cost=bool(include_cost),
        )
        report["reliability_metrics"] = {
            "metrics": rc.metrics,
            "node_latency_p95": rc.node_latency_p95,
        }
        report["metrics"].update(rc.metrics)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--dataset", default="tests/data/questions.json")
    parser.add_argument("--persist-dir", default=".milvus")
    parser.add_argument("--artifacts-dir", default=".artifacts")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--baseline-report", default="")
    parser.add_argument("--compare-report", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--stage", default="")
    parser.add_argument("--stage-notes", default="")
    parser.add_argument("--profile", default="all", choices=["all", "retrieval", "gate", "reliability"])
    parser.add_argument("--retrieval-k", default="1,3,5")
    parser.add_argument("--include-cost", action="store_true")
    parser.add_argument("--include-latency", action="store_true")
    parser.add_argument("--with-gate", action="store_true")
    parser.add_argument("--enforce-thresholds", action="store_true")
    parser.add_argument("--thresholds", default="docs/eval_thresholds.yaml")
    parser.add_argument("--enable-ragas", action="store_true", help="Enable RAGAS metrics (faithfulness, answer_relevancy, context_precision, etc.)")
    parser.add_argument("--enable-citation-judge", action="store_true", help="Enable citation judge for verifying answer citations")
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

    enable_ragas = bool(args.enable_ragas) or _env_bool("EVAL_ENABLE_RAGAS")
    stage = str(args.stage).lower().strip()
    allowed_stages = {"step1", "step2", "step3", "step4"}
    if stage in allowed_stages and not os.getenv("RISKAGENT_RETRIEVER_MODE"):
        os.environ["RISKAGENT_RETRIEVER_MODE"] = stage
    if stage in allowed_stages and not os.getenv("RISKAGENT_RERANKER_MODEL"):
        os.environ["RISKAGENT_RERANKER_MODEL"] = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    if bool(args.enable_citation_judge):
        os.environ["EVAL_ENABLE_CITATION_JUDGE"] = "true"
        os.environ["EVAL_CITATION_JUDGE_MODE"] = "llm"
    os.environ["EVAL_NUMERIC_TOLERANCE"] = str(float(args.numeric_tolerance))
    retrieval_ks = _parse_retrieval_ks(str(args.retrieval_k))
    include_latency = bool(args.include_latency) or str(args.profile).strip().lower() == "reliability"
    include_cost = bool(args.include_cost) or str(args.profile).strip().lower() == "reliability"

    report = run_evaluation(
        corpus_dir=corpus_dir,
        dataset_path=dataset_path,
        persist_dir=persist_dir,
        enable_ragas=enable_ragas,
        profile=str(args.profile),
        retrieval_ks=retrieval_ks,
        include_cost=include_cost,
        include_latency=include_latency,
        with_gate=bool(args.with_gate),
    )
    if args.stage or args.stage_notes:
        report["stage"] = {
            **_stage_plan(str(args.stage)),
            "notes": str(args.stage_notes).strip(),
        }

    baseline_path = args.compare_report or args.baseline_report or args.baseline or find_latest_report(
        artifacts_dir=args.artifacts_dir
    )
    diff: dict[str, Any] | None = None
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

    if bool(args.enforce_thresholds):
        cfg = load_thresholds(str(args.thresholds))
        gate = evaluate_threshold_gate(
            report=report,
            baseline_diff=diff,
            config=cfg,
        )
        report["threshold_gate"] = gate

    label = str(args.label).strip()
    if not label and args.stage:
        label = str(args.stage).strip()
    out_path = write_report(report, artifacts_dir=args.artifacts_dir, label=label)
    print(f"JSON Report: {out_path}")
    
    # Generate Markdown report
    md_path = Path(out_path).with_suffix('.md')
    try:
        generate_markdown_report(
            report_data=report,
            output_path=md_path,
            title=f"RAG Evaluation Report - {label or 'default'}",
            include_raw_scores=False,
        )
        print(f"Markdown Report: {md_path}")
    except Exception as e:
        print(f"Warning: Failed to generate Markdown report: {e}", file=os.sys.stderr)
    
    if bool(args.enforce_thresholds):
        verdict = ((report.get("threshold_gate") or {}).get("verdict") or "pass").strip().lower()
        if verdict == "fail":
            raise SystemExit(2)


if __name__ == "__main__":
    main()
