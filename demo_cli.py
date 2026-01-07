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
    parser.add_argument("--persist-dir", default=str(_project_root() / ".chroma"))
    parser.add_argument("--out", default=str(_project_root() / "logs" / "demo_result.json"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    project_root = _project_root()
    _ensure_src_on_path(project_root)

    from riskagent_rag.graph.workflow import build_rag_graph
    from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

    sources_dir = pathlib.Path(args.sources_dir)
    persist_dir = pathlib.Path(args.persist_dir)

    if args.rebuild_index:
        # 技术难点: 语料变化后必须 rebuild index, 否则 citations 会指向旧内容.
        # Week 2 会把 rebuild 作为日常回归的一部分.
        build_index(sources_dir=sources_dir, persist_dir=persist_dir)

    vectorstore = load_index(persist_dir)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    graph = build_rag_graph(retriever)

    request_id = str(uuid.uuid4())
    # 技术难点: request_id 便于把一次问答的输入输出与日志关联.
    # Week 2 引入评测脚本时, request_id 也便于落盘与对比.
    out = graph.invoke({"question": args.question})

    answer = out.get("answer", "")
    docs = out.get("docs", [])
    citations = extract_citations(docs)

    result = {
        "request_id": request_id,
        "question": args.question,
        "answer": answer,
        "citations": citations,
        "sources_dir": str(sources_dir),
        "persist_dir": str(persist_dir),
    }

    # 技术难点: 输出落盘是 Week 2 的基础.
    # - 没有 artifacts 就无法做回归对比, 也无法量化 citations coverage.

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
