from __future__ import annotations

import argparse
import os
from pathlib import Path

from pydantic import SecretStr

from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.evaluation.report_generator import generate_markdown_report
from riskagent_agenticrag.evaluation.reporting import write_report
from riskagent_agenticrag.evaluation.run import run_evaluation
from riskagent_agenticrag.evaluation.thresholds import evaluate_threshold_gate, load_thresholds


def _require_env(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _resolve_override(name: str) -> str:
    override_name = f"RISKAGENT_OVERRIDE_{name}"
    value = str(os.getenv(override_name, "")).strip()
    if value:
        return value
    return _require_env(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--artifacts-dir", default=".artifacts_fresh")
    parser.add_argument("--dataset-path", default="tests/data/questions.json")
    parser.add_argument("--embeddings-model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()

    # 中文注释: 直接覆盖进程内 settings, 避免项目 .env 在导入时覆盖外部环境变量.
    settings.llm.api_key = SecretStr(_resolve_override("LLM_API_KEY"))
    settings.llm.openai_api_key = None
    settings.llm.base_url = _resolve_override("LLM_BASE_URL")
    settings.llm.model = _resolve_override("LLM_MODEL")
    settings.embeddings.provider = "hf"
    settings.embeddings.model_name = str(args.embeddings_model).strip()

    report = run_evaluation(
        corpus_dir=Path("corpus"),
        dataset_path=Path(str(args.dataset_path)),
        persist_dir=Path(".milvus"),
        enable_ragas=False,
        profile="all",
        retrieval_ks=[1, 3, 5],
        include_cost=False,
        include_latency=False,
        with_gate=True,
    )
    config = load_thresholds("config/eval_thresholds.json")
    gate = evaluate_threshold_gate(report=report, baseline_diff=None, config=config)
    report["threshold_gate"] = gate

    json_path = write_report(report, artifacts_dir=str(args.artifacts_dir), label=str(args.label))
    md_path = Path(json_path).with_suffix(".md")
    generate_markdown_report(
        report_data=report,
        output_path=md_path,
        title=f"RAG Evaluation Report - {args.label}",
        include_raw_scores=False,
    )

    print(f"JSON Report: {json_path}")
    print(f"Markdown Report: {md_path}")
    print(f"Threshold Verdict: {gate.get('verdict')}")


if __name__ == "__main__":
    main()
