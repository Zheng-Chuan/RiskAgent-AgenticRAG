from __future__ import annotations

import argparse
import os
import time
import urllib.request
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


def _debug_emit(hypothesis_id: str, msg: str, *, data: dict[str, object] | None = None) -> None:
    # #region debug-point D:script-wrapper
    env_path = Path(".dbg/report-hang.env")
    debug_url = "http://127.0.0.1:7777/event"
    session_id = "report-hang"
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("DEBUG_SERVER_URL="):
                debug_url = line.split("=", 1)[1].strip() or debug_url
            elif line.startswith("DEBUG_SESSION_ID="):
                session_id = line.split("=", 1)[1].strip() or session_id
    except Exception:
        return
    payload = {
        "sessionId": session_id,
        "runId": str(os.getenv("RISKAGENT_DEBUG_RUN_ID", "pre-fix") or "pre-fix"),
        "hypothesisId": hypothesis_id,
        "location": "scripts.run_fresh_eval_with_current_env",
        "msg": f"[DEBUG] {msg}",
        "data": data or {},
        "ts": int(time.time() * 1000),
    }
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                debug_url,
                data=str(__import__("json").dumps(payload, ensure_ascii=False)).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.8,
        ).read()
    except Exception:
        pass
    # #endregion


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
    # 中文注释: full baseline 默认打开 judge 进度输出和保守并发, 既保证尽量跑完,
    # 也让外部能区分"正常慢"和"异常卡死".
    os.environ.setdefault("EVAL_CITATION_JUDGE_PROGRESS", "true")
    os.environ.setdefault("EVAL_CITATION_JUDGE_MAX_CONCURRENCY", "4")
    os.environ.setdefault("EVAL_CITATION_JUDGE_HEARTBEAT_SEC", "10")

    _debug_emit("D", "script_run_evaluation_start", data={"label": str(args.label), "dataset": str(args.dataset_path)})
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
    _debug_emit("D", "script_run_evaluation_done", data={"metric_count": len(report.get("metrics", {})), "samples": len(report.get("samples", []))})
    config = load_thresholds("config/eval_thresholds.json")
    _debug_emit("D", "threshold_gate_start", data={"label": str(args.label)})
    gate = evaluate_threshold_gate(report=report, baseline_diff=None, config=config)
    report["threshold_gate"] = gate
    _debug_emit("D", "threshold_gate_done", data={"verdict": str(gate.get("verdict") or "")})

    _debug_emit("D", "write_report_start", data={"artifacts_dir": str(args.artifacts_dir)})
    json_path = write_report(report, artifacts_dir=str(args.artifacts_dir), label=str(args.label))
    _debug_emit("D", "write_report_done", data={"json_path": json_path})
    md_path = Path(json_path).with_suffix(".md")
    _debug_emit("D", "markdown_report_start", data={"md_path": str(md_path)})
    generate_markdown_report(
        report_data=report,
        output_path=md_path,
        title=f"RAG Evaluation Report - {args.label}",
        include_raw_scores=False,
    )
    _debug_emit("D", "markdown_report_done", data={"md_path": str(md_path)})

    print(f"JSON Report: {json_path}")
    print(f"Markdown Report: {md_path}")
    print(f"Threshold Verdict: {gate.get('verdict')}")


if __name__ == "__main__":
    main()
