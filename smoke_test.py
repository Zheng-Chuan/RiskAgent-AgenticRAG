from __future__ import annotations

import json
import pathlib
import sys


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def _ensure_src_on_path(project_root: pathlib.Path) -> None:
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        # 技术难点: 为了让 smoke test 可直接运行, 这里做了 path 注入.
        sys.path.insert(0, str(src_dir))


def main() -> None:
    project_root = _project_root()
    _ensure_src_on_path(project_root)

    from riskagent_rag.graph.workflow import build_rag_graph
    from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index

    sources_dir = project_root / "docs" / "sources"
    persist_dir = project_root / ".chroma"
    out_dir = project_root / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    build_index(sources_dir=sources_dir, persist_dir=persist_dir)

    # 技术难点: smoke test 必须覆盖 ingest -> retrieve -> answer 的最短路径.
    # - 目标不是回答质量, 而是保证关键链路不回归.

    vectorstore = load_index(persist_dir)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    graph = build_rag_graph(retriever)

    question = "what is FRTB"
    out = graph.invoke({"question": question})

    answer = out.get("answer", "")
    docs = out.get("docs", [])
    citations = extract_citations(docs)

    result = {
        "question": question,
        "answer": answer,
        "citations": citations,
    }
    (out_dir / "smoke_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not answer:
        raise SystemExit("smoke failed: empty answer")

    if not citations:
        raise SystemExit("smoke failed: empty citations")

    # 业务不清晰点: 什么算有效 citations.
    # - 这里只做最保守检查: citations 非空且能定位到 docs/sources.
    # - Week 2 会用 20 个问题集定义更严格的引用覆盖率指标.

    # Minimal check: citations should point to docs/sources.
    first_source = str(citations[0].get("source", ""))
    if "docs/sources" not in first_source.replace("\\", "/"):
        raise SystemExit(f"smoke failed: unexpected citation source: {first_source}")

    print("OK: smoke passed")


if __name__ == "__main__":
    main()
