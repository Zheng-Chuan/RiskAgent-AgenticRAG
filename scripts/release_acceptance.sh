#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RUNNER=()
if command -v conda >/dev/null 2>&1; then
  if conda env list | awk '{print $1}' | grep -qx "agenticrag"; then
    RUNNER=(conda run -n agenticrag)
  elif conda env list | awk '{print $1}' | grep -qx "riskagent-agenticrag"; then
    RUNNER=(conda run -n riskagent-agenticrag)
  elif conda env list | awk '{print $1}' | grep -qx "LangChain"; then
    RUNNER=(conda run -n LangChain)
  fi
fi

run_in_selected_env() {
  if [ "${#RUNNER[@]}" -gt 0 ]; then
    "${RUNNER[@]}" "$@"
  else
    "$@"
  fi
}

run_in_selected_env bash scripts/run_offline_regression.sh

run_in_selected_env python - <<'PY'
import os
from pathlib import Path

from riskagent_agenticrag.evaluation.reporting import load_report
from riskagent_agenticrag.evaluation.thresholds import evaluate_threshold_gate, load_thresholds

threshold_path = Path("config/eval_thresholds.json")
config = load_thresholds(threshold_path)
sample_report_path = Path(".artifacts/reports/rag_eval_baseline_sample.json")

llm_key = (
    os.getenv("OPENAI_API_KEY", "").strip()
    or os.getenv("LLM_API_KEY", "").strip()
)
fresh_report_path = None

if llm_key:
    from riskagent_agenticrag.evaluation.run import run_evaluation

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
    gate = evaluate_threshold_gate(
        report=report,
        baseline_diff=None,
        config=config,
    )
    report["threshold_gate"] = gate
    assert report.get("answer_eval", {}).get("ok") is True
    assert report.get("retrieval_metrics", {}).get("gold_metrics")
    assert report.get("threshold_gate", {}).get("verdict") in {"pass", "warning"}
    print("release acceptance passed with fresh evaluation")
else:
    report = load_report(sample_report_path)
    gate = evaluate_threshold_gate(
        report=report,
        baseline_diff=((report.get("baseline") or {}).get("diff")),
        config=config,
    )
    assert report.get("answer_eval", {}).get("ok") is True
    assert report.get("retrieval_metrics", {}).get("gold_metrics")
    assert report.get("threshold_gate", {}).get("verdict") == "pass"
    assert gate.get("verdict") in {"pass", "warning"}
    print("release acceptance passed with sample baseline fallback")
PY
