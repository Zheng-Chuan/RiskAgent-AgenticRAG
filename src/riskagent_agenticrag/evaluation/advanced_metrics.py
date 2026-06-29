from __future__ import annotations

import math
import os
from dataclasses import dataclass
from statistics import mean
from typing import Any

@dataclass(frozen=True)
class RetrievalMetrics:
    metrics: dict[str, float]
    slice_metrics: dict[str, dict[str, float]]


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


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _normalize_id(value: Any) -> str:
    return str(value or "").strip()


def _sample_qrels(sample: dict[str, Any]) -> list[dict[str, Any]]:
    raw = sample.get("qrels")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for row in raw:
        if isinstance(row, dict):
            out.append(row)
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


def _row_haystacks(row: dict[str, Any]) -> list[str]:
    content = _normalize_text(str(row.get("content") or row.get("text") or row.get("snippet") or ""))
    expanded = _normalize_text(str(row.get("expanded_text") or ""))
    return [text for text in (content, expanded) if text]


def _row_matches_qrel(row: dict[str, Any], qrel: dict[str, Any]) -> bool:
    row_chunk_id = _normalize_id(row.get("chunk_id"))
    qrel_chunk_id = _normalize_id(qrel.get("chunk_id"))
    if qrel_chunk_id:
        return bool(row_chunk_id) and row_chunk_id == qrel_chunk_id

    row_source = _normalize_id(row.get("source"))
    qrel_source = _normalize_id(qrel.get("source"))
    row_section_path = _normalize_id(row.get("section_path"))
    qrel_section_path = _normalize_id(qrel.get("section_path"))
    row_parent_id = _normalize_id(row.get("parent_id"))
    qrel_parent_id = _normalize_id(qrel.get("parent_id"))
    haystacks = _row_haystacks(row)
    target = _normalize_text(str(qrel.get("text") or ""))

    if qrel_source and row_source and qrel_source == row_source:
        if qrel_section_path and row_section_path and qrel_section_path == row_section_path:
            return True
        if qrel_parent_id and row_parent_id and qrel_parent_id == row_parent_id:
            return True
        if target:
            for haystack in haystacks:
                if target in haystack or haystack in target:
                    return True

    if not haystacks:
        return False
    if not target:
        return False
    for haystack in haystacks:
        if target in haystack or haystack in target:
            return True
    return False


def _matched_qrel_ids(row: dict[str, Any], qrels: list[dict[str, Any]]) -> list[str]:
    matches: list[str] = []
    for index, qrel in enumerate(qrels, start=1):
        if not _row_matches_qrel(row, qrel):
            continue
        qrel_id = _normalize_id(qrel.get("qrel_id")) or f"qrel_{index}"
        if qrel_id not in matches:
            matches.append(qrel_id)
    return matches


def _is_row_relevant(row: dict[str, Any], qrels: list[dict[str, Any]]) -> bool:
    return bool(_matched_qrel_ids(row, qrels))


def _compute_single_retrieval_metrics(sample: dict[str, Any], ks: list[int]) -> dict[str, float]:
    qrels = _sample_qrels(sample)
    rows = _retrieved_rows(sample)
    if not qrels:
        metrics = {"retrieval_mrr": 0.0}
        for k in ks:
            metrics[f"retrieval_recall_at_{k}"] = 0.0
            metrics[f"retrieval_ndcg_at_{k}"] = 0.0
        return metrics

    qrel_relevance = {
        (_normalize_id(qrel.get("qrel_id")) or f"qrel_{index}"): max(1, int(qrel.get("relevance", 1)))
        for index, qrel in enumerate(qrels, start=1)
    }
    matched_qrels: dict[str, int] = {}
    matched_relevance: dict[int, int] = {}
    first_rank = 0
    has_dense = False
    has_sparse = False
    for idx, row in enumerate(rows, start=1):
        if row.get("dense_rank") is not None:
            has_dense = True
        if row.get("sparse_rank") is not None:
            has_sparse = True
        row_qrel_ids = _matched_qrel_ids(row, qrels)
        if not row_qrel_ids:
            continue
        if first_rank == 0:
            first_rank = idx
        matched_relevance[idx] = max(
            int(matched_relevance.get(idx, 0)),
            max(qrel_relevance.get(qrel_id, 1) for qrel_id in row_qrel_ids),
        )
        for qrel_id in row_qrel_ids:
            matched_qrels.setdefault(qrel_id, idx)

    total_relevant = len(qrel_relevance)
    metrics: dict[str, float] = {
        "retrieval_mrr": 1.0 / float(first_rank) if first_rank > 0 else 0.0,
        "retrieval_dense_hit_rate": 1.0 if has_dense else 0.0,
        "retrieval_sparse_hit_rate": 1.0 if has_sparse else 0.0,
        "retrieval_hybrid_gain_rate": 1.0 if has_dense and has_sparse and first_rank > 0 else 0.0,
        "retrieval_rerank_uplift": 0.0,
    }

    rel_rrf = [(_to_float(r.get("rrf_score")), i + 1) for i, r in enumerate(rows) if _is_row_relevant(r, qrels)]
    rel_rerank = [(_to_float(r.get("rerank_score")), i + 1) for i, r in enumerate(rows) if _is_row_relevant(r, qrels)]
    if rel_rrf and rel_rerank:
        rrf_best = max(rel_rrf, key=lambda x: x[0])[1]
        rerank_best = max(rel_rerank, key=lambda x: x[0])[1]
        metrics["retrieval_rerank_uplift"] = float(rrf_best - rerank_best)

    for k in ks:
        hits = sum(1 for position in matched_qrels.values() if position <= k)
        metrics[f"retrieval_recall_at_{k}"] = float(hits) / float(max(1, total_relevant))

        dcg = 0.0
        for position, relevance in matched_relevance.items():
            if position > k:
                continue
            dcg += (2.0 ** float(relevance) - 1.0) / math.log2(float(position) + 1.0)
        ranked_relevance = sorted((int(q.get("relevance", 1)) for q in qrels), reverse=True)[:k]
        idcg = 0.0
        for i, relevance in enumerate(ranked_relevance, start=1):
            idcg += (2.0 ** float(relevance) - 1.0) / math.log2(float(i) + 1.0)
        metrics[f"retrieval_ndcg_at_{k}"] = (dcg / idcg) if idcg > 0 else 0.0
    return metrics


def compute_retrieval_metrics(samples: list[dict[str, Any]], *, ks: list[int]) -> RetrievalMetrics:
    clean_ks = sorted({int(k) for k in ks if int(k) > 0})
    if not clean_ks:
        clean_ks = [1, 3, 5]

    per_sample = [_compute_single_retrieval_metrics(sample, clean_ks) for sample in samples]
    if not per_sample:
        empty: dict[str, float] = {"retrieval_mrr": 0.0}
        for k in clean_ks:
            empty[f"retrieval_recall_at_{k}"] = 0.0
            empty[f"retrieval_ndcg_at_{k}"] = 0.0
        return RetrievalMetrics(metrics=empty, slice_metrics={})

    metric_names = sorted({name for sample_metrics in per_sample for name in sample_metrics})
    metrics: dict[str, float] = {}
    for name in metric_names:
        values = [float(sample_metrics.get(name, 0.0)) for sample_metrics in per_sample]
        metrics[name] = float(mean(values)) if values else 0.0

    slice_metrics: dict[str, dict[str, float]] = {}
    grouped_samples: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        tags = sample.get("tags")
        if not isinstance(tags, list):
            continue
        for tag in tags:
            key = str(tag).strip()
            if not key:
                continue
            grouped_samples.setdefault(key, []).append(sample)
    for tag, subset in grouped_samples.items():
        subset_metrics = [_compute_single_retrieval_metrics(sample, clean_ks) for sample in subset]
        slice_metrics[tag] = {
            name: float(mean([float(row.get(name, 0.0)) for row in subset_metrics])) if subset_metrics else 0.0
            for name in metric_names
        }

    return RetrievalMetrics(metrics=metrics, slice_metrics=slice_metrics)


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
    labeled_total = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0

    for sample in samples:
        status = str(sample.get("status") or "")
        is_blocked = status != "ok"
        if is_blocked:
            blocked += 1

        gate_label = sample.get("gate_label")
        should_block = None
        if isinstance(gate_label, dict) and "should_block" in gate_label:
            should_block = bool(gate_label.get("should_block"))
        if should_block is not None:
            labeled_total += 1
            if is_blocked and should_block:
                true_positive += 1
                blocked_beneficial += 1
            elif is_blocked and not should_block:
                false_positive += 1
                blocked_false_kill += 1
            elif (not is_blocked) and should_block:
                false_negative += 1
        key = _failure_reason_key(sample.get("failure_reason")) if is_blocked else "ok"
        dist[key] = int(dist.get(key, 0)) + 1

    denominator = float(max(1, labeled_total))
    metrics = {
        "gate_block_rate": float(blocked) / float(total),
        "gate_block_benefit_rate": float(blocked_beneficial) / denominator,
        "gate_false_kill_rate": float(blocked_false_kill) / denominator,
        "gate_miss_rate": float(false_negative) / denominator,
    }
    return GateMetrics(
        metrics=metrics,
        distributions={
            "failure_reason_distribution": dist,
            "labeled_counts": {
                "labeled_total": labeled_total,
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
            },
        },
    )


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
