from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from riskagent_rag.evaluation.dataset import load_dataset
from riskagent_rag.graph.workflow import build_rag_graph
from riskagent_rag.llm.generate import _format_context, generate_answer
from riskagent_rag.rag.pipeline import build_index, extract_citations, load_index


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round((len(values) - 1) * p))))
    return float(values[k])


def _maybe_count_tokens(*, text: str, model: str) -> Optional[int]:
    try:
        import tiktoken
    except Exception:
        return None

    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    try:
        return int(len(enc.encode(text)))
    except Exception:
        return None


def _build_prompt_for_cost(*, question: str, docs: list[Any]) -> str:
    context = _format_context(docs, limit=1600)
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider == "ollama":
        return (
            "You are a helpful assistant explaining financial derivatives and risk concepts to software engineers. "
            "Answer using only the provided context. If context is insufficient, say you do not know. "
            "Keep the answer concise and include next actions when refusing.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n"
        )
    return (
        "You are a helpful assistant explaining financial derivatives and risk concepts to software engineers. "
        "Answer using only the provided context. If context is insufficient, say you do not know.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}\n"
    )


@dataclass(frozen=True)
class TimingStats:
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float


def _timing_stats(values_s: list[float]) -> TimingStats:
    values_ms = [v * 1000.0 for v in values_s]
    if not values_ms:
        return TimingStats(count=0, mean_ms=0.0, p50_ms=0.0, p95_ms=0.0, max_ms=0.0)
    return TimingStats(
        count=len(values_ms),
        mean_ms=float(statistics.fmean(values_ms)),
        p50_ms=_percentile(values_ms, 0.50),
        p95_ms=_percentile(values_ms, 0.95),
        max_ms=float(max(values_ms)),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--dataset", default="tests/data/questions.json")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    dataset_path = Path(args.dataset)
    runs = max(1, int(args.runs))
    k = max(1, int(args.k))

    items = load_dataset(dataset_path)

    index_times: list[float] = []
    retrieve_times: list[float] = []
    generate_times: list[float] = []
    e2e_times: list[float] = []
    token_counts: list[int] = []

    with tempfile.TemporaryDirectory() as td:
        persist_dir = Path(td) / "milvus"

        for _ in range(runs):
            t0 = time.perf_counter()
            build_index(sources_dir=corpus_dir, persist_dir=persist_dir)
            index_times.append(time.perf_counter() - t0)

            vectorstore = load_index(persist_dir)
            retriever = vectorstore.as_retriever(search_kwargs={"k": k})
            graph = build_rag_graph(retriever)

            for item in items:
                question = str(item.question)
                t_all = time.perf_counter()

                t_r = time.perf_counter()
                out = graph.invoke({"question": question})
                docs = out.get("docs", [])
                retrieve_times.append(time.perf_counter() - t_r)

                t_g = time.perf_counter()
                answer = generate_answer(question, docs)
                generate_times.append(time.perf_counter() - t_g)

                citations = extract_citations(docs)
                _ = len(citations)
                _ = len(answer)
                e2e_times.append(time.perf_counter() - t_all)

                model = os.getenv("LLM_MODEL", "gpt-4o-mini")
                prompt = _build_prompt_for_cost(question=question, docs=docs)
                tok = _maybe_count_tokens(text=prompt, model=model)
                if tok is not None:
                    token_counts.append(tok)

    report: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "inputs": {
            "corpus_dir": str(corpus_dir),
            "dataset": str(dataset_path),
            "runs": runs,
            "k": k,
            "llm_provider": os.getenv("LLM_PROVIDER", ""),
            "llm_model": os.getenv("LLM_MODEL", ""),
        },
        "env": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "timings": {
            "index_build": asdict(_timing_stats(index_times)),
            "retrieve_plus_graph": asdict(_timing_stats(retrieve_times)),
            "generate_answer_only": asdict(_timing_stats(generate_times)),
            "e2e_per_question": asdict(_timing_stats(e2e_times)),
        },
        "tokens": {
            "counted": bool(token_counts),
            "prompt_tokens_mean": float(statistics.fmean(token_counts)) if token_counts else 0.0,
            "prompt_tokens_p95": _percentile([float(x) for x in token_counts], 0.95) if token_counts else 0.0,
        },
    }

    out_path = args.out.strip()
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(p))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

