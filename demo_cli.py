from __future__ import annotations

import argparse
import json
import pathlib
import sys
import uuid


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _ensure_src_on_path(project_root: pathlib.Path) -> None:
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        # 技术难点: 为了让脚本可直接运行, 这里做了 path 注入.
        # 后续如果引入 pyproject.toml 并 pip install -e ., 可以移除这个 hack.
        sys.path.insert(0, str(src_dir))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--sources-dir", default=str(_project_root() / "docs" / "sources"))
    parser.add_argument("--persist-dir", default=str(_project_root() / ".milvus"))
    parser.add_argument("--out", default=str(_project_root() / "logs" / "demo_result.json"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    project_root = _project_root()
    _ensure_src_on_path(project_root)

    from riskagent_rag.orchestration.langgraph_runner import run_langgraph_agentic_chat
    from riskagent_rag.rag.agentic_loop import run_agentic_chat
    from riskagent_rag.rag.pipeline import build_index, load_index

    sources_dir = pathlib.Path(args.sources_dir)
    persist_dir = pathlib.Path(args.persist_dir)

    if args.rebuild_index:
        # 技术难点: 语料变化后必须 rebuild index, 否则 citations 会指向旧内容.
        # Week 2 会把 rebuild 作为日常回归的一部分.
        build_index(sources_dir=sources_dir, persist_dir=persist_dir)

    # Load index and retriever
    vectorstore = load_index(persist_dir)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    # Check Environment Variable
    import os
    use_langgraph = os.getenv("USE_LANGGRAPH", "").lower().strip() in ("true", "1", "yes")
    
    print(f"Running with: use_langgraph={use_langgraph}")

    if use_langgraph:
        out = run_langgraph_agentic_chat(question=args.question, retriever=retriever)
    else:
        out = run_agentic_chat(question=args.question, retriever=retriever)

    # Extract results
    answer = out.get("answer", "")
    citations = out.get("citations", [])
    claims = out.get("claims", [])
    evidence_set = out.get("evidence_set", [])
    decision_log = out.get("decision_log", [])
    tool_traces = out.get("tool_traces", [])
    status = out.get("status", "ok")
    failure_reason = out.get("failure_reason")

    result = {
        "request_id": str(uuid.uuid4()), # Note: run_langgraph_agentic_chat might generate its own request_id internally for artifacts, but here we generate one for CLI output wrapping
        "question": args.question,
        "answer": answer,
        "citations": citations,
        "claims": claims,
        "evidence_set": evidence_set,
        "decision_log": decision_log,
        "tool_traces": tool_traces,
        "status": status,
        "failure_reason": failure_reason,
        "sources_dir": str(sources_dir),
        "persist_dir": str(persist_dir),
        "runner": "langgraph" if use_langgraph else "agentic_loop"
    }

    # 技术难点: 输出落盘是 Week 2 的基础.
    # - 没有 artifacts 就无法做回归对比, 也无法量化 citations coverage.

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
