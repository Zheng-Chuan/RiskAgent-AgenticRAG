"""Performance / Concurrency Tests -- 并发场景: Token追踪、缓存、治理公平性、内存稳定性."""

from __future__ import annotations

import socket
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from riskagent_agenticrag.llm.generate import call_llm_text
from riskagent_agenticrag.llm.governance import LLMGovernanceError, get_llm_cost_governor
from riskagent_agenticrag.llm.token_tracker import get_token_tracker

# ---------------------------------------------------------------------------
# Infrastructure check
# ---------------------------------------------------------------------------

def _llm_available() -> bool:
    """Check if LLM API is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(("ark.cn-beijing.volces.com", 443))
        sock.close()
        return result == 0
    except Exception:
        return False


skip_no_llm = pytest.mark.skipif(not _llm_available(), reason="LLM API not reachable")

_PROMPT = "Define market risk in one sentence."
_CACHE_PROMPT = "What is Value at Risk (VaR)? Answer in exactly one sentence."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.performance
@skip_no_llm
def test_perf_token_budget_under_load():
    """10 concurrent calls — verify token tracker accuracy (total matches sum)."""
    tracker = get_token_tracker()
    usage_before = tracker.get_usage()
    tokens_before = usage_before["total_tokens"]

    results: list[tuple[str | None, Exception | None]] = []

    def _call():
        try:
            return call_llm_text(_PROMPT, temperature=0.3), None
        except Exception as exc:
            return None, exc

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_call) for _ in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[1] is None]
    assert len(successes) >= 5, f"Too few successes: {len(successes)}/10"

    usage_after = tracker.get_usage()
    tokens_after = usage_after["total_tokens"]
    tokens_consumed = tokens_after - tokens_before

    # Token tracker should have recorded tokens for all successful calls
    assert tokens_consumed > 0, "Token tracker recorded zero tokens after 10 calls"
    # Each call consumes at least some tokens
    assert tokens_consumed >= len(successes) * 10, (
        f"Token consumption {tokens_consumed} too low for {len(successes)} calls"
    )


@pytest.mark.performance
@skip_no_llm
def test_perf_cache_hit_ratio_under_load():
    """10 identical requests with temp=0 — verify cache improves after first."""
    # First call: populate cache
    t0 = time.time()
    call_llm_text(_CACHE_PROMPT, temperature=0.0)
    first_latency = time.time() - t0

    # Second batch: 10 identical calls (should hit cache)
    latencies: list[float] = []

    def _cached_call():
        start = time.time()
        call_llm_text(_CACHE_PROMPT, temperature=0.0)
        return time.time() - start

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_cached_call) for _ in range(10)]
        for f in as_completed(futures):
            latencies.append(f.result())

    avg_cached = sum(latencies) / len(latencies)

    # Cache hits should be at least 50% faster than the initial uncached call
    assert avg_cached < first_latency * 0.5, (
        f"Cached avg {avg_cached:.3f}s not 50% faster than first call {first_latency:.3f}s"
    )


@pytest.mark.performance
@skip_no_llm
def test_perf_governance_fairness():
    """Mix of 'default' and 'non_critical' priority — verify non_critical blocked first."""
    default_blocked = 0
    non_critical_blocked = 0

    def _call_with_priority(priority: str):
        try:
            call_llm_text(_PROMPT, priority=priority, estimated_tokens=4096)
            return priority, True
        except LLMGovernanceError:
            return priority, False
        except Exception:
            return priority, True  # non-governance errors count as not-blocked

    tasks = []
    # Interleave priorities: 10 default + 10 non_critical
    for _ in range(10):
        tasks.append("default")
        tasks.append("non_critical")

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_call_with_priority, p) for p in tasks]
        for f in as_completed(futures):
            priority, succeeded = f.result()
            if not succeeded:
                if priority == "default":
                    default_blocked += 1
                else:
                    non_critical_blocked += 1

    # If any blocking occurred, non_critical should be blocked at least as much
    if default_blocked + non_critical_blocked > 0:
        assert non_critical_blocked >= default_blocked, (
            f"Fairness violation: default blocked={default_blocked}, "
            f"non_critical blocked={non_critical_blocked}"
        )


@pytest.mark.performance
@skip_no_llm
def test_perf_memory_usage_stability():
    """Run 20 requests — check memory usage doesn't grow unbounded."""
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    results: list[tuple[str | None, Exception | None]] = []

    def _call():
        try:
            return call_llm_text(_PROMPT, temperature=0.1), None
        except Exception as exc:
            return None, exc

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_call) for _ in range(20)]
        for f in as_completed(futures):
            results.append(f.result())

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Compare top memory consumers
    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_growth_mb = sum(s.size_diff for s in stats) / (1024 * 1024)

    # Memory growth should be < 50 MB for 20 requests
    assert total_growth_mb < 50.0, (
        f"Memory grew by {total_growth_mb:.2f} MB over 20 requests (limit: 50 MB)"
    )


@pytest.mark.performance
@skip_no_llm
def test_perf_sustained_load_60s():
    """Send 1 request/second for 60 seconds — verify no degradation."""
    latencies: list[float] = []
    errors: list[Exception] = []

    for _ in range(60):
        t0 = time.time()
        try:
            call_llm_text(_PROMPT, temperature=0.0)
            latencies.append(time.time() - t0)
        except LLMGovernanceError:
            # Governance blocks are acceptable under sustained load
            latencies.append(time.time() - t0)
        except Exception as exc:
            errors.append(exc)
            latencies.append(time.time() - t0)

        # Pace: 1 request per second
        elapsed = time.time() - t0
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

    # Error rate should be < 50%
    error_rate = len(errors) / 60.0
    assert error_rate < 0.5, f"Error rate {error_rate:.0%} too high over 60s sustained load"

    # No degradation: last 10 latencies should not be > 3x the first 10 average
    if len(latencies) >= 20:
        first_10_avg = sum(latencies[:10]) / 10.0
        last_10_avg = sum(latencies[-10:]) / 10.0
        if first_10_avg > 0:
            degradation_ratio = last_10_avg / first_10_avg
            assert degradation_ratio < 3.0, (
                f"Latency degradation {degradation_ratio:.1f}x "
                f"(first 10 avg={first_10_avg:.2f}s, last 10 avg={last_10_avg:.2f}s)"
            )
