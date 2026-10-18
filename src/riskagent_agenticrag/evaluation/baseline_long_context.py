"""长上下文基线对比实验 (RFC-006 B).

两种模式同一题集同一 judge 对比, 回答 "为什么不全量塞进 128k 上下文":
- parent_stuffing: parent 语料按检索相关性排序, 塞满长上下文窗口后一次作答
- rag_main: 现有统一检索主链 (对照)

统一指标: faithfulness / answer_relevancy / numeric_consistency / refusal 率 /
latency p50 p95 / token 成本. 指标序列附带 bootstrap 95% CI (RFC-006 A2 复用).

注: 曾设计 map_reduce_full (全语料逐段抽取再汇总) 模式, 实测每题需遍历
577 段 (约 2.9h/题) 且收益无望超过检索主链, 已于 2026-10-18 移除.
产出对比报告 (JSON + markdown) 落 docs/evaluations/.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from riskagent_agenticrag.evaluation.advanced_metrics import (
    _quantile,
    bootstrap_mean_ci,
)
from riskagent_agenticrag.evaluation.citations import is_valid_citation
from riskagent_agenticrag.evaluation.dataset import load_dataset
from riskagent_agenticrag.evaluation.domain_consistency import (
    try_compute_domain_consistency,
)
from riskagent_agenticrag.evaluation.ragas_metrics import compute_all_ragas_metrics
from riskagent_agenticrag.evaluation.refusal import is_refusal_answer

# token 估算口径与 llm/generate.py 一致 (chars // 4)
_CHARS_PER_TOKEN = 4

MODES = ("rag_main", "parent_stuffing")

_LLMCall = Callable[[str], str]


# ---------------------------------------------------------------------------
# parent 塞窗 (parent_stuffing 用)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PackedContext:
    text: str
    used_parent_ids: list[str]
    used_chars: int
    truncated: bool


def pack_parents(
    ordered_parent_ids: list[str],
    parents_by_id: dict[str, Any],
    *,
    window_tokens: int,
) -> PackedContext:
    """按相关性顺序把 parent 全文塞进窗口, 装满即止 (后续 parent 丢弃).

    返回打包文本 + 实际使用的 parent id 列表, truncated 表示窗口不够装下全部 parent.
    """
    max_chars = max(1, int(window_tokens)) * _CHARS_PER_TOKEN
    parts: list[str] = []
    used: list[str] = []
    total = 0
    truncated = False
    seen: set[str] = set()
    for pid in ordered_parent_ids:
        key = str(pid or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        parent = parents_by_id.get(key)
        if parent is None:
            continue
        text = str(getattr(parent, "page_content", "") or "").strip()
        if not text:
            continue
        block = f"[source: {(parent.metadata or {}).get('source', '')}]\n{text}"
        if total + len(block) + 2 > max_chars:
            truncated = True
            break
        parts.append(block)
        used.append(key)
        total += len(block) + 2
    return PackedContext(
        text="\n\n".join(parts),
        used_parent_ids=used,
        used_chars=total,
        truncated=truncated,
    )


def ordered_parent_ids_from_docs(docs: list[Any]) -> list[str]:
    """从检索返回的 chunk 列表按顺序抽取去重后的 parent_id."""
    ids: list[str] = []
    seen: set[str] = set()
    for d in docs:
        meta = getattr(d, "metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}
        pid = str(meta.get("parent_id") or "").strip()
        if pid and pid not in seen:
            seen.add(pid)
            ids.append(pid)
    return ids


# ---------------------------------------------------------------------------
# LLM 调用封装: 统一记录 latency 与 token 用量
# ---------------------------------------------------------------------------

@dataclass
class CallStat:
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _call_with_stat(
    llm_call: _LLMCall, prompt: str, *, max_retries: int = 5, base_wait_s: float = 3.0
) -> tuple[str, CallStat]:
    t0 = time.perf_counter()
    text: str | None = None
    # 长实验串行大量 LLM 调用, governance 令牌桶耗尽会抛 rate_limited 异常;
    # 不重试会让整题直接标 error (实验早期跑批 10 题全崩的原因).
    for attempt in range(max_retries + 1):
        try:
            text = llm_call(prompt)
            break
        except Exception as exc:
            msg = str(exc)
            if "rate_limited" not in msg or attempt >= max_retries:
                raise
            wait = base_wait_s * (attempt + 1)
            for tok in msg.replace("'", '"').replace("}", "").split('"'):
                try:
                    wait = float(tok)
                    break
                except ValueError:
                    continue
            time.sleep(min(wait, 60.0))
    assert text is not None
    latency = (time.perf_counter() - t0) * 1000.0
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        from riskagent_agenticrag.llm.generate import get_last_token_usage

        usage = get_last_token_usage() or usage
    except Exception:
        pass
    pt = int(usage.get("prompt_tokens", 0) or 0)
    ct = int(usage.get("completion_tokens", 0) or 0)
    if pt == 0 and ct == 0:
        # 估算口径与主链一致
        pt = len(prompt) // _CHARS_PER_TOKEN
        ct = len(str(text)) // _CHARS_PER_TOKEN
    return str(text), CallStat(latency_ms=latency, prompt_tokens=pt, completion_tokens=ct)


_ANSWER_INSTRUCTIONS = (
    "Answer STRICTLY using only facts from the provided context.\n"
    "Every number in your answer MUST appear verbatim in the context.\n"
    "If the context contains nothing usable, say you do not know.\n"
)


# ---------------------------------------------------------------------------
# 三种模式 runner: 每题输出统一 sample 结构
# id/question/answer/contexts/reference_answer/reference_contexts/
# latency_ms/prompt_tokens/completion_tokens/status/refusal
# ---------------------------------------------------------------------------

def _base_sample(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.item_id),
        "question": str(item.question),
        "reference_answer": item.reference_answer,
        "reference_contexts": item.reference_contexts,
        "answer": "",
        "contexts": [],
        "latency_ms": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "status": "ok",
        "refusal": False,
    }


def run_parent_stuffing(
    items: list[Any],
    *,
    retriever: Any,
    parents_by_id: dict[str, Any],
    llm_call: _LLMCall,
    window_tokens: int = 128_000,
    retrieval_k: int = 32,
    judge_context_chars: int = 2000,
) -> list[dict[str, Any]]:
    """RAG 最强朴素变体: 检索信号只用来排序 parent, 上下文塞满窗口后一次作答."""
    samples: list[dict[str, Any]] = []
    for item in items:
        sample = _base_sample(item)
        question = sample["question"]
        t0 = time.perf_counter()
        prompt_tokens = 0
        completion_tokens = 0
        try:
            docs = list(retriever.invoke(question) or [])[:retrieval_k]
            packed = pack_parents(
                ordered_parent_ids_from_docs(docs),
                parents_by_id,
                window_tokens=window_tokens,
            )
            answer_prompt = (
                "You are a precise assistant explaining financial derivatives and risk concepts.\n"
                f"{_ANSWER_INSTRUCTIONS}\n"
                f"Question: {question}\n\n"
                f"Context (full parent documents ordered by relevance):\n{packed.text or '(empty)'}"
            )
            answer, stat = _call_with_stat(llm_call, answer_prompt)
            sample["answer"] = answer.strip()
            sample["contexts"] = [
                packed.text[i : i + judge_context_chars]
                for i in range(0, min(len(packed.text), judge_context_chars * 4), judge_context_chars)
            ]
            sample["used_parent_count"] = len(packed.used_parent_ids)
            sample["window_truncated"] = packed.truncated
            prompt_tokens = stat.prompt_tokens
            completion_tokens = stat.completion_tokens
        except Exception as exc:
            sample["status"] = f"error: {exc}"
        sample["latency_ms"] = (time.perf_counter() - t0) * 1000.0
        sample["prompt_tokens"] = prompt_tokens
        sample["completion_tokens"] = completion_tokens
        sample["refusal"] = is_refusal_answer(answer=sample["answer"], citations=[])
        samples.append(sample)
    return samples


def run_rag_main(items: list[Any], *, retriever: Any) -> list[dict[str, Any]]:
    """对照模式: 现有统一检索主链 (LangGraph agentic loop)."""
    from riskagent_agenticrag.orchestration.langgraph_runner import (
        run_langgraph_agentic_chat,
    )

    samples: list[dict[str, Any]] = []
    for item in items:
        sample = _base_sample(item)
        question = sample["question"]
        t0 = time.perf_counter()
        try:
            out = run_langgraph_agentic_chat(question=question, retriever=retriever)
            answer = str(out.get("answer", ""))
            docs = out.get("docs", [])
            citations = out.get("citations")
            if not isinstance(citations, list):
                citations = []
            contexts: list[str] = []
            for d in docs[:4]:
                meta = getattr(d, "metadata", {}) or {}
                if not isinstance(meta, dict):
                    meta = {}
                text = str(meta.get("expanded_text") or getattr(d, "page_content", "") or "").strip()
                if text:
                    contexts.append(text[:1800])
            sample["answer"] = answer
            sample["contexts"] = contexts
            sample["status"] = str(out.get("status") or "")
            valid = [c for c in citations if isinstance(c, dict) and is_valid_citation(c)]
            sample["refusal"] = is_refusal_answer(answer=answer, citations=valid)
            # 主链 token 用量按字符估算 (口径与 reliability metrics 一致)
            sample["prompt_tokens"] = (len(question) + sum(len(c) for c in contexts)) // _CHARS_PER_TOKEN
            sample["completion_tokens"] = len(answer) // _CHARS_PER_TOKEN
        except Exception as exc:
            sample["status"] = f"error: {exc}"
        sample["latency_ms"] = (time.perf_counter() - t0) * 1000.0
        samples.append(sample)
    return samples


# ---------------------------------------------------------------------------
# 统一指标聚合
# ---------------------------------------------------------------------------

def aggregate_run_stats(samples: list[dict[str, Any]]) -> dict[str, float]:
    latencies = [float(s.get("latency_ms", 0.0) or 0.0) for s in samples]
    prompt_tokens = [float(s.get("prompt_tokens", 0) or 0) for s in samples]
    completion_tokens = [float(s.get("completion_tokens", 0) or 0) for s in samples]
    n = len(samples)
    return {
        "n": float(n),
        "latency_p50_ms": _quantile(latencies, 0.50),
        "latency_p95_ms": _quantile(latencies, 0.95),
        "prompt_tokens_mean": float(mean(prompt_tokens)) if prompt_tokens else 0.0,
        "completion_tokens_mean": float(mean(completion_tokens)) if completion_tokens else 0.0,
        "total_tokens_mean": (
            float(mean([p + c for p, c in zip(prompt_tokens, completion_tokens, strict=True)]))
            if prompt_tokens
            else 0.0
        ),
        "refusal_rate": float(sum(1 for s in samples if s.get("refusal"))) / float(max(1, n)),
        "error_rate": float(sum(1 for s in samples if str(s.get("status", "")).startswith("error"))) / float(max(1, n)),
    }


def evaluate_mode_samples(
    samples: list[dict[str, Any]],
    *,
    enable_ragas: bool = True,
) -> dict[str, Any]:
    """对单模式的 samples 计算统一指标 (与主评测同一 judge 与口径)."""
    out: dict[str, Any] = {"run_stats": aggregate_run_stats(samples), "metrics": {}}

    ragas_result: Any = None
    if enable_ragas and samples:
        ragas_result = compute_all_ragas_metrics(
            samples=samples,
            include_reference_based=True,
            include_context_precision=True,
            include_low_priority=False,
        )
    if ragas_result is not None:
        out["ragas"] = {
            "enabled": ragas_result.enabled,
            "ok": ragas_result.ok,
            "metrics": ragas_result.metrics,
            "raw_scores": ragas_result.raw_scores,
            "error": ragas_result.error,
        }
        if ragas_result.ok:
            for key in ("ragas_faithfulness", "ragas_answer_relevancy"):
                if key in ragas_result.metrics:
                    out["metrics"][key.replace("ragas_", "")] = float(ragas_result.metrics[key])

    domain = try_compute_domain_consistency(samples=samples, tolerance=0.01)
    out["domain_consistency"] = {
        "enabled": domain.enabled,
        "ok": domain.ok,
        "metrics": domain.metrics,
        "error": domain.error,
    }
    if domain.ok and isinstance(domain.metrics, dict):
        for key, value in domain.metrics.items():
            try:
                out["metrics"][key] = float(value)
            except (TypeError, ValueError):
                pass

    # bootstrap CI (RFC-006 A2): faithfulness/answer_relevancy 用 RAGAS 逐题分,
    # numeric_consistency 用 domain per-sample 分
    ci_series: dict[str, list[float]] = {}
    if ragas_result is not None and getattr(ragas_result, "ok", False):
        raw = ragas_result.raw_scores or {}
        for src, dst in (
            ("faithfulness", "faithfulness"),
            ("answer_relevancy", "answer_relevancy"),
        ):
            values = raw.get(src) or []
            if values:
                ci_series[dst] = [float(v) for v in values]
    if domain.ok:
        per_sample = (domain.details or {}).get("samples", [])
        numeric_values = []
        for row in per_sample:
            if isinstance(row, dict):
                try:
                    numeric_values.append(float((row.get("numeric") or {}).get("score")))
                except (TypeError, ValueError):
                    pass
        if numeric_values:
            ci_series["numeric_consistency_score"] = numeric_values
    confidence: dict[str, dict[str, float]] = {}
    for name, values in ci_series.items():
        ci = bootstrap_mean_ci(values)
        if ci is not None:
            confidence[name] = ci
    out["confidence_intervals"] = confidence
    return out


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def build_comparison_report(
    mode_results: dict[str, dict[str, Any]],
    *,
    modes: list[str],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "experiment": "long_context_baseline",
        "rfc": "RFC-006 B",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "meta": meta,
        "modes": modes,
        "results": mode_results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    modes = report.get("modes", [])
    lines: list[str] = []
    lines.append("# 长上下文基线对比实验 (RFC-006 B)")
    lines.append("")
    meta = report.get("meta", {})
    lines.append(f"- 生成时间: {report.get('generated_at', '')}")
    lines.append(f"- 题集: {meta.get('dataset', '')} (n={meta.get('n_questions', 0)})")
    lines.append(f"- 窗口: {meta.get('window_tokens', '')} tokens")
    lines.append("")
    lines.append("## 统一指标对比")
    lines.append("")
    lines.append(
        "| Metric | " + " | ".join(modes) + " |"
    )
    lines.append("|--------|" + "|".join(["-----"] * len(modes)) + "|")

    results = report.get("results", {})

    def _fmt_ci(mode: str, metric: str) -> str:
        ci = ((results.get(mode) or {}).get("confidence_intervals") or {}).get(metric)
        if not isinstance(ci, dict):
            return ""
        return f" (95% CI {ci.get('ci_low', 0):.3f}-{ci.get('ci_high', 0):.3f})"

    def _metric(mode: str, key: str) -> str:
        value = (results.get(mode) or {}).get("metrics", {}).get(key)
        if value is None:
            return "-"
        return f"{float(value):.3f}"

    rows = [
        ("faithfulness", False),
        ("answer_relevancy", False),
        ("numeric_consistency_score", False),
        ("refusal_rate", False),
        ("error_rate", False),
    ]
    for key, _ in rows:
        cells = []
        for mode in modes:
            cell = _metric(mode, key)
            if cell != "-":
                cell += _fmt_ci(mode, key)
            cells.append(cell)
        lines.append(f"| {key} | " + " | ".join(cells) + " |")

    stats_rows = [
        ("latency_p50_ms", "latency p50 (ms)"),
        ("latency_p95_ms", "latency p95 (ms)"),
        ("prompt_tokens_mean", "prompt tokens/题"),
        ("completion_tokens_mean", "completion tokens/题"),
        ("total_tokens_mean", "total tokens/题"),
    ]
    for key, label in stats_rows:
        cells = []
        for mode in modes:
            value = (results.get(mode) or {}).get("run_stats", {}).get(key)
            cells.append(f"{float(value):,.0f}" if value is not None else "-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- parent_stuffing: 检索排序 + 塞满窗口; rag_main: 现有主链对照. (曾设计 map_reduce_full 全量知识模式, 因每题 ~2.9h 成本于 2026-10-18 移除)")
    lines.append("- CI 为单题级 bootstrap (1000 次重采样, percentile 法). 题集不含负例题, refusal_rate 为误拒率, 越低越好.")
    lines.append("- 本报告为一次性实验产出, 结论是否纳入每期评测对照列见对应 ADR.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 实验编排
# ---------------------------------------------------------------------------

def run_baseline_experiment(
    *,
    corpus_dir: Path,
    dataset_path: Path,
    persist_dir: Path,
    modes: list[str],
    limit: int = 0,
    window_tokens: int = 128_000,
    out_dir: Path | None = None,
    enable_ragas: bool = True,
    llm_call: _LLMCall | None = None,
    retriever: Any = None,
) -> dict[str, Any]:
    """编排三模式实验并落盘对比报告. llm_call/retriever 可注入用于测试."""
    from riskagent_agenticrag.llm.generate import call_llm_text

    resolved_llm: _LLMCall = llm_call or call_llm_text

    unknown = [m for m in modes if m not in MODES]
    if unknown:
        raise ValueError(f"unknown modes: {unknown}; valid: {MODES}")

    items = load_dataset(dataset_path)
    if limit and limit > 0:
        items = items[: int(limit)]

    mode_results: dict[str, dict[str, Any]] = {}

    need_retriever = any(m in modes for m in ("rag_main", "parent_stuffing"))
    if need_retriever and retriever is None:
        from riskagent_agenticrag.rag.retriever_factory import build_retriever

        retriever = build_retriever(persist_dir=persist_dir, final_k=32)

    parents_by_id: dict[str, Any] = {}
    if "parent_stuffing" in modes:
        from riskagent_agenticrag.rag.advanced_index import parent_corpus_by_id

        parents_by_id = parent_corpus_by_id(persist_dir=persist_dir)

    for mode in modes:
        started = time.perf_counter()
        if mode == "rag_main":
            samples = run_rag_main(items, retriever=retriever)
        else:
            samples = run_parent_stuffing(
                items,
                retriever=retriever,
                parents_by_id=parents_by_id,
                llm_call=resolved_llm,
                window_tokens=window_tokens,
            )
        result = evaluate_mode_samples(samples, enable_ragas=enable_ragas)
        result["samples"] = samples
        result["wall_time_s"] = time.perf_counter() - started
        mode_results[mode] = result

    report = build_comparison_report(
        mode_results,
        modes=list(modes),
        meta={
            "corpus_dir": str(corpus_dir),
            "dataset": str(dataset_path),
            "n_questions": len(items),
            "window_tokens": int(window_tokens),
        },
    )

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # samples 明细较大, 单独落盘, 主报告只留指标
        slim = {m: {k: v for k, v in r.items() if k != "samples"} for m, r in mode_results.items()}
        report["results"] = slim
        json_path = out_dir / f"long_context_baseline_{stamp}.json"
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        md_path = out_dir / f"long_context_baseline_{stamp}.md"
        md_path.write_text(render_markdown(report), encoding="utf-8")
        report["output_json"] = str(json_path)
        report["output_markdown"] = str(md_path)

    return report


def main() -> None:
    import argparse
    import logging

    logging.basicConfig(
        level=os.getenv("RISKAGENT_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="RFC-006 B: 长上下文基线对比实验")
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--dataset", default="tests/data/questions.json")
    parser.add_argument("--persist-dir", default=".milvus")
    parser.add_argument("--modes", default=",".join(MODES))
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 题 (0=全部)")
    parser.add_argument("--window-tokens", type=int, default=128_000)
    parser.add_argument("--out-dir", default="docs/evaluations")
    parser.add_argument("--no-ragas", action="store_true", help="跳过 RAGAS judge (只看延迟/成本)")
    args = parser.parse_args()

    report = run_baseline_experiment(
        corpus_dir=Path(args.corpus_dir),
        dataset_path=Path(args.dataset),
        persist_dir=Path(args.persist_dir),
        modes=[m.strip() for m in str(args.modes).split(",") if m.strip()],
        limit=int(args.limit),
        window_tokens=int(args.window_tokens),
        out_dir=Path(args.out_dir),
        enable_ragas=not args.no_ragas,
    )
    print(json.dumps({"output_json": report.get("output_json"), "output_markdown": report.get("output_markdown")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
