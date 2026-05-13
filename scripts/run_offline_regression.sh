#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export EVAL_CITATION_JUDGE_MODE=heuristic
export RISKAGENT_ENABLE_LLM_APPEAL=false
export EMBEDDINGS_PROVIDER=hash
# 隔离共享 conda 环境里的第三方 pytest 插件 避免收集阶段被无关插件破坏
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

python -m pytest \
  tests/test_api_v1.py \
  tests/test_contract_langgraph.py \
  tests/test_contract_artifacts_validator.py \
  tests/test_failure_taxonomy_coverage.py \
  tests/test_milestone1_acceptance.py \
  tests/test_milestone2_acceptance.py \
  tests/test_milestone3_acceptance.py \
  tests/test_citation_precision.py \
  tests/test_domain_consistency.py \
  tests/test_evaluation_dataset.py \
  tests/test_advanced_metrics.py \
  tests/test_answer_eval.py \
  tests/test_threshold_gate.py \
  tests/test_evaluation_reporting.py \
  -q
