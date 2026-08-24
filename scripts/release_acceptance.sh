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

# 发布验收必须跑 fresh eval, 无 LLM key 直接报错终止, 不再回退样例报告
if [ -z "${OPENAI_API_KEY:-}${LLM_API_KEY:-}" ]; then
  echo "ERROR: release acceptance requires a fresh evaluation run." >&2
  echo "Set OPENAI_API_KEY or LLM_API_KEY and re-run. Sample-report fallback has been removed." >&2
  exit 1
fi

run_in_selected_env python - <<'PY'
from pathlib import Path

from riskagent_agenticrag.evaluation.run import run_evaluation
from riskagent_agenticrag.evaluation.thresholds import evaluate_threshold_gate, load_thresholds

config = load_thresholds(Path("config/eval_thresholds.json"))

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
PY
