from __future__ import annotations

import math
import os
from dataclasses import dataclass
from statistics import mean
from typing import Any

from riskagent_rag.evaluation.citations import is_valid_citation


@dataclass(frozen=True)
class RetrievalMetrics:
    metrics: dict[str, float]


@dataclass(frozen=True)
class GateMetrics:
    metrics: dict[str, float]
    distributions: dict[str, Any]


@dataclass(frozen=True)
class ReliabilityCostMetrics:
    metrics: dict[str, float]
    node_latency_p95: dict[str, float]


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * min(max(q, 0.0), 1.0)
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return float(xs[low])
    frac = pos - low
    return float(xs[low] * (1.0 - frac) + xs[high] * frac)


def _metric_key_relevance_id(source: str, chunk_id: str) -> str:
    return f"{source}::{chunk_id}"


def _relevant_doc_ids_from_sample(sample: dict[str, Any]) -> set[str]:
    raw = sample.get("citations")
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for c in raw:
        if not isinstance(c, dict):
            continue
        if not is_valid_citation(c):
            continue
        source = str(c.get("source") or "")
        chunk_id = str(c.get("chunk_id") or "")
        if source and chunk_id:
            out.add(_metric_key_relevance_id(source, chunk_id))
    return out


def _retrieved_rows(sample: dict[str, Any]) -> list[dict[str, Any]]:
    rows = sample.get("retrieved_docs")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def compute_retrieval_metrics(samples: list[dict[str, Any]], *, ks: list[int]) -> RetrievalMetrics:
    clean_ks = sorted({int(k) for k in ks if int(k) > 0})
    if not clean_ks:
        clean_ks = [1, 3, 5]

    recall_hits: dict[int, int] = {k: 0 for k in clean_ks}
    ndcg_sum: dict[int, float] = {k: 0.0 for k in clean_ks}
    mrr_scores: list[float] = []
    dense_hits = 0
    sparse_hits = 0
    hybrid_gains = 0
    rerank_improvements: list[float] = []
    total = max(1, len(samples))

    for sample in samples:
        relevant = _relevant_doc_ids_from_sample(sample)
        rows = _retrieved_rows(sample)
        first_rank = 0
        rel_positions: list[int] = []
        has_dense = False
        has_sparse = False

        for idx, row in enumerate(rows, start=1):
            source = str(row.get("source") or "")
            chunk_id = str(row.get("chunk_id") or "")
            if row.get("dense_rank") is not None:
                has_dense = True
            if row.get("sparse_rank") is not None:
                has_sparse = True
            if not source or not chunk_id:
                continue
            rid = _metric_key_relevance_id(source, chunk_id)
            if rid in relevant:
                rel_positions.append(idx)
                if first_rank == 0:
                    first_rank = idx

        if has_dense:
            dense_hits += 1
        if has_sparse:
            sparse_hits += 1
        if has_dense and has_sparse and first_rank > 0:
            hybrid_gains += 1
        if first_rank > 0:
            mrr_scores.append(1.0 / float(first_rank))
        else:
            mrr_scores.append(0.0)

        for k in clean_ks:
            if first_rank > 0 and first_rank <= k:
                recall_hits[k] += 1

            dcg = 0.0
            for p in rel_positions:
                if p > k:
                    continue
                dcg += 1.0 / math.log2(float(p) + 1.0)
            ideal_rel = min(len(relevant), k)
            idcg = 0.0
            for i in range(1, ideal_rel + 1):
                idcg += 1.0 / math.log2(float(i) + 1.0)
            ndcg_sum[k] += (dcg / idcg) if idcg > 0 else 0.0

        rel_rrf = [(_to_float(r.get("rrf_score")), i + 1) for i, r in enumerate(rows) if _metric_key_relevance_id(str(r.get("source") or ""), str(r.get("chunk_id") or "")) in relevant]
        rel_rerank = [(_to_float(r.get("rerank_score")), i + 1) for i, r in enumerate(rows) if _metric_key_relevance_id(str(r.get("source") or ""), str(r.get("chunk_id") or "")) in relevant]
        if rel_rrf and rel_rerank:
            rrf_best = max(rel_rrf, key=lambda x: x[0])[1]
            rerank_best = max(rel_rerank, key=lambda x: x[0])[1]
            rerank_improvements.append(float(rrf_best - rerank_best))

    metrics: dict[str, float] = {
        "retrieval_mrr": float(mean(mrr_scores)) if mrr_scores else 0.0,
        "retrieval_dense_hit_rate": float(dense_hits) / float(total),
        "retrieval_sparse_hit_rate": float(sparse_hits) / float(total),
        "retrieval_hybrid_gain_rate": float(hybrid_gains) / float(total),
        "retrieval_rerank_uplift": float(mean(rerank_improvements)) if rerank_improvements else 0.0,
    }
    for k in clean_ks:
        metrics[f"retrieval_recall_at_{k}"] = float(recall_hits[k]) / float(total)
        metrics[f"retrieval_ndcg_at_{k}"] = float(ndcg_sum[k]) / float(total)
    return RetrievalMetrics(metrics=metrics)


def _failure_reason_key(raw: Any) -> str:
    if raw is None:
        return "none"
    if isinstance(raw, dict):
        code = str(raw.get("code") or "").strip()
        message = str(raw.get("message") or "").strip()
        if code:
            return code
        if message:
            return message[:80]
    text = str(raw).strip()
    return text[:80] if text else "unknown"


def compute_gate_metrics(samples: list[dict[str, Any]]) -> GateMetrics:
    total = max(1, len(samples))
    blocked = 0
    blocked_beneficial = 0
    blocked_false_kill = 0
    dist: dict[str, int] = {}

    for sample in samples:
        status = str(sample.get("status") or "")
        is_blocked = status != "ok"
        if is_blocked:
            blocked += 1
        answer = str(sample.get("answer") or "").strip()
        valid_count = int(sample.get("valid_citation_count") or 0)
        if is_blocked and (not answer or valid_count == 0):
            blocked_beneficial += 1
        if is_blocked and answer and valid_count > 0:
            blocked_false_kill += 1
        key = _failure_reason_key(sample.get("failure_reason")) if is_blocked else "ok"
        dist[key] = int(dist.get(key, 0)) + 1

    metrics = {
        "gate_block_rate": float(blocked) / float(total),
        "gate_block_benefit_rate": float(blocked_beneficial) / float(total),
        "gate_false_kill_rate": float(blocked_false_kill) / float(total),
    }
    return GateMetrics(metrics=metrics, distributions={"failure_reason_distribution": dist})


def compute_reliability_cost_metrics(
    samples: list[dict[str, Any]],
    *,
    include_latency: bool,
    include_cost: bool,
) -> ReliabilityCostMetrics:
    total = max(1, len(samples))
    success = 0
    errors = 0
    timeouts = 0
    latencies: list[float] = []
    node_series: dict[str, list[float]] = {}
    prompt_tokens: list[float] = []
    completion_tokens: list[float] = []
    cache_hits = 0

    price_prompt = _to_float(os.getenv("EVAL_COST_PROMPT_PER_1K", "0"))
    price_completion = _to_float(os.getenv("EVAL_COST_COMPLETION_PER_1K", "0"))

    for sample in samples:
        status = str(sample.get("status") or "")
        if status == "ok":
            success += 1
        else:
            errors += 1
            reason = _failure_reason_key(sample.get("failure_reason")).lower()
            if "timeout" in reason or "timed out" in reason:
                timeouts += 1

        latency = _to_float(sample.get("latency_ms"), -1.0)
        if include_latency and latency >= 0.0:
            latencies.append(latency)
        raw_nodes = sample.get("node_latencies")
        if include_latency and isinstance(raw_nodes, dict):
            for k, v in raw_nodes.items():
                vv = _to_float(v, -1.0)
                if vv < 0.0:
                    continue
                node_series.setdefault(str(k), []).append(vv)

        if include_cost:
            q = str(sample.get("question") or "")
            ctx = sample.get("contexts")
            context_text = ""
            if isinstance(ctx, list):
                context_text = "\n".join(str(x) for x in ctx)
            a = str(sample.get("answer") or "")
            pt = max(0.0, float(len(q) + len(context_text)) / 4.0)
            ct = max(0.0, float(len(a)) / 4.0)
            prompt_tokens.append(pt)
            completion_tokens.append(ct)
            if bool(sample.get("cache_hit", False)):
                cache_hits += 1

    metrics: dict[str, float] = {
        "reliability_success_rate": float(success) / float(total),
        "reliability_error_rate": float(errors) / float(total),
        "reliability_timeout_rate": float(timeouts) / float(total),
    }
    node_p95: dict[str, float] = {}
    if include_latency:
        metrics["latency_p50_ms"] = _quantile(latencies, 0.50)
        metrics["latency_p95_ms"] = _quantile(latencies, 0.95)
        metrics["latency_p99_ms"] = _quantile(latencies, 0.99)
        for k, series in node_series.items():
            node_p95[k] = _quantile(series, 0.95)
    if include_cost:
        prompt_mean = float(mean(prompt_tokens)) if prompt_tokens else 0.0
        completion_mean = float(mean(completion_tokens)) if completion_tokens else 0.0
        total_tokens_mean = prompt_mean + completion_mean
        metrics["cost_estimated_prompt_tokens"] = prompt_mean
        metrics["cost_estimated_completion_tokens"] = completion_mean
        metrics["cost_estimated_total_tokens"] = total_tokens_mean
        metrics["cost_estimated_usd"] = (prompt_mean / 1000.0) * price_prompt + (completion_mean / 1000.0) * price_completion
        metrics["cache_hit_rate"] = float(cache_hits) / float(total)
    return ReliabilityCostMetrics(metrics=metrics, node_latency_p95=node_p95)
