#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

RUNNER=()
if command -v conda >/dev/null 2>&1; then
  if conda env list | awk '{print $1}' | grep -qx "riskagent-agenticrag"; then
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
from pathlib import Path

from riskagent_agenticrag.evaluation.reporting import load_report
from riskagent_agenticrag.evaluation.thresholds import evaluate_threshold_gate, load_thresholds

report_path = Path(".artifacts/reports/rag_eval_baseline_sample.json")
threshold_path = Path("config/eval_thresholds.json")

report = load_report(report_path)
config = load_thresholds(threshold_path)
gate = evaluate_threshold_gate(
    report=report,
    baseline_diff=((report.get("baseline") or {}).get("diff")),
    config=config,
)

assert report.get("answer_eval", {}).get("ok") is True
assert report.get("retrieval_metrics", {}).get("gold_metrics")
assert report.get("threshold_gate", {}).get("verdict") == "pass"
assert gate.get("verdict") in {"pass", "warning"}
print("release acceptance passed")
PY
