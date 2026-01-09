from __future__ import annotations

import argparse
import json
import pathlib
import sys


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _ensure_src_on_path(project_root: pathlib.Path) -> None:
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        # 技术难点: 为了让评测脚本可直接运行, 这里做了 path 注入.
        sys.path.insert(0, str(src_dir))


def _parse_args() -> argparse.Namespace:
    project_root = _project_root()

    p = argparse.ArgumentParser()
    p.add_argument(
        "--questions",
        default=str(project_root / "scripts" / "questions.json"),
    )
    p.add_argument(
        "--sources-dir",
        default=str(project_root / "docs" / "sources"),
    )
    p.add_argument("--persist-dir", default=str(project_root / ".chroma"))
    p.add_argument(
        "--out",
        default=str(project_root / "logs" / "eval_summary.json"),
    )
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--rebuild-index", action="store_true")
    return p.parse_args()


def _is_valid_citation(c: dict) -> bool:
    source = str(c.get("source", ""))
    chunk_id = str(c.get("chunk_id", ""))
    if not source or not chunk_id:
        return False
    # Week 1/2 的最小验收口径: source 必须能回指到 docs/sources.
    return "docs/sources" in source.replace("\\", "/")


def main() -> None:
    project_root = _project_root()
    _ensure_src_on_path(project_root)
    args = _parse_args()

    from riskagent_rag.graph.workflow import build_rag_graph
    from riskagent_rag.rag.pipeline import (
        build_index,
        extract_citations,
        load_index,
    )

    questions_path = pathlib.Path(args.questions)
    items = json.loads(questions_path.read_text(encoding="utf-8"))

    sources_dir = pathlib.Path(args.sources_dir)
    persist_dir = pathlib.Path(args.persist_dir)

    if args.rebuild_index:
        build_index(sources_dir=sources_dir, persist_dir=persist_dir)

    vectorstore = load_index(persist_dir)
    retriever = vectorstore.as_retriever(search_kwargs={"k": args.k})
    graph = build_rag_graph(retriever)

    rows: list[dict] = []
    ok = 0

    for item in items:
        qid = str(item.get("id", ""))
        question = str(item.get("question", ""))
        out = graph.invoke({"question": question})

        answer = out.get("answer", "")
        docs = out.get("docs", [])
        citations = extract_citations(docs)

        valid_citations = [c for c in citations if _is_valid_citation(c)]
        passed = bool(answer) and bool(valid_citations)
        if passed:
            ok += 1

        rows.append(
            {
                "id": qid,
                "question": question,
                "passed": passed,
                "answer_len": len(str(answer)),
                "citation_count": len(citations),
                "valid_citation_count": len(valid_citations),
                "citations": citations,
            }
        )

    total = len(rows)
    coverage = (ok / total) if total else 0.0

    summary = {
        "total": total,
        "passed": ok,
        "coverage": coverage,
        "settings": {
            "sources_dir": str(sources_dir),
            "persist_dir": str(persist_dir),
            "k": args.k,
            "rebuild_index": bool(args.rebuild_index),
        },
        "results": rows,
    }

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "coverage": coverage,
                "passed": ok,
                "total": total,
                "out": str(out_path),
            }
        )
    )


if __name__ == "__main__":
    main()
