from __future__ import annotations

import argparse
import json
import pathlib
import sys
import uuid
from pathlib import Path

from riskagent_agenticrag.app import RiskAgentSystem
from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.indexing.indexer import incremental_index


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="riskagent_agenticrag.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_index = sub.add_parser("index", help="Incrementally index corpus into vector store")
    p_index.add_argument("--corpus-dir", default=str(settings.paths.corpus_dir))
    p_index.add_argument("--persist-dir", default=str(settings.paths.milvus_lite_dir))
    p_index.add_argument("--path", action="append", default=[], help="Index only specified file path (repeatable).")

    p_ask = sub.add_parser("ask", help="Ask a question using the indexed corpus (requires LLM)")
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--max-rounds", type=int, default=2)
    p_ask.add_argument("--out", default="")

    p_chat = sub.add_parser("chat", help="Interactive chat (requires LLM)")
    p_chat.add_argument("--max-rounds", type=int, default=2)

    sub.add_parser("status", help="Show current configuration")
    return p


def _require_llm() -> None:
    if not settings.llm.api_key:
        raise RuntimeError("Missing OpenRouter API key. Set OPENAI_API_KEY (or LLM_API_KEY).")


def _cmd_index(args: argparse.Namespace) -> int:
    corpus_dir = Path(str(args.corpus_dir))
    persist_dir = Path(str(args.persist_dir))
    include = [Path(p) for p in (args.path or []) if str(p or "").strip()]
    result = incremental_index(corpus_dir=corpus_dir, persist_dir=persist_dir, include_paths=include or None)
    print("Index updated")
    print(f"- corpus_dir: {corpus_dir}")
    print(f"- persist_dir: {result.persist_dir}")
    print(f"- indexed_sources: {len(result.indexed_sources)}")
    print(f"- skipped_sources: {len(result.skipped_sources)}")
    print(f"- chunk_indexed: {result.chunk_indexed}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    _require_llm()
    system = RiskAgentSystem()
    request_id = f"cli-{uuid.uuid4().hex[:12]}"
    out = system.chat(str(args.question), max_rounds=int(args.max_rounds), request_id=request_id)
    if str(args.out or "").strip():
        out_path = pathlib.Path(str(args.out)).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if str(out.get("status") or "") == "error":
        return 2
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    _require_llm()
    system = RiskAgentSystem()
    history: list[tuple[str, str]] = []
    print("Enter chat mode. Type 'exit' to quit.")
    while True:
        user_text = input("> ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        request_id = f"cli-{uuid.uuid4().hex[:12]}"
        out = system.chat(user_text, history=history, max_rounds=int(args.max_rounds), request_id=request_id)
        answer = str(out.get("answer", "")).strip() or str(out.get("message", "")).strip()
        print(answer)
        history.append((user_text, answer))
    return 0


def _cmd_status() -> int:
    print("LLM")
    print(f"- base_url: {settings.llm.base_url}")
    print(f"- model: {settings.llm.model}")
    print(f"- api_key_ok: {bool(settings.llm.api_key)}")
    print("Paths")
    print(f"- corpus_dir: {settings.paths.corpus_dir}")
    print(f"- persist_dir: {settings.paths.milvus_lite_dir}")
    return 0


def main() -> None:
    p = _build_parser()
    args = p.parse_args()
    try:
        if args.cmd == "index":
            code = _cmd_index(args)
        elif args.cmd == "ask":
            code = _cmd_ask(args)
        elif args.cmd == "chat":
            code = _cmd_chat(args)
        elif args.cmd == "status":
            code = _cmd_status()
        else:
            raise RuntimeError(f"unknown command: {args.cmd}")
    except Exception as exc:
        msg = str(exc).strip() or exc.__class__.__name__
        print(f"ERROR: {msg}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
