from __future__ import annotations

import argparse
import json
import pathlib
import uuid

from riskagent_rag.app import system
from riskagent_rag.config.settings import settings


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="")
    parser.add_argument("--chat", action="store_true")
    # 默认值通过 settings 获取, 但允许 CLI 覆盖 (虽然 settings 目前写死了一些路径, 但可扩展)
    # 为了简化 CLI, 暂移除手动指定 dir 的参数，或者让它们覆盖 settings (暂未实现 settings 动态覆盖)
    # 这里保持原有参数以兼容旧习惯，但实际 system 内部使用的是 settings.
    # TODO: 让 CLI 参数能动态修改 settings  # pylint: disable=fixme
    parser.add_argument("--out", default=str(_project_root() / "logs" / "demo_result.json"))
    args = parser.parse_args()
    if not args.chat and not str(args.question or "").strip():
        parser.error("--question is required unless --chat is set")
    return args


def main() -> None:
    args = _parse_args()
    print("Indexing is CLI-only. Run: python -m riskagent_rag.cli.index --corpus-dir corpus --persist-dir .milvus")

    if args.chat:
        history: list[tuple[str, str]] = []
        print("Enter chat mode. Type 'exit' to quit.")
        while True:
            user_text = input("> ").strip()
            if user_text.lower() in {"exit", "quit"}:
                break
            out = system.chat(question=user_text, history=history)
            answer = str(out.get("answer", ""))
            print(answer)
            history.append((user_text, answer))
        return

    out = system.chat(question=args.question)

    result = {
        "request_id": str(uuid.uuid4()),
        "question": args.question,
        "answer": out.get("answer", ""),
        "citations": out.get("citations", []),
        "claims": out.get("claims", []),
        "evidence_set": out.get("evidence_set", []),
        "decision_log": out.get("decision_log", []),
        "tool_traces": out.get("tool_traces", []),
        "status": out.get("status", "ok"),
        "failure_reason": out.get("failure_reason"),
        "sources_dir": str(settings.paths.corpus_dir),
        "persist_dir": str(settings.paths.milvus_lite_dir),
        "runner": out.get("runner", "unknown"),
    }

    # 技术难点: 输出落盘是 Week 2 的基础.
    # - 没有 artifacts 就无法做回归对比, 也无法量化 citations coverage.

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
