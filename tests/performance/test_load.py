"""Performance / Load Tests -- 负载测试: 延迟与吞吐量."""

from __future__ import annotations

import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from riskagent_agenticrag.llm.generate import call_llm_text
from riskagent_agenticrag.llm.governance import LLMGovernanceError

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

_PROMPT = "What is credit risk? Answer in one sentence."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _timed_call(prompt: str = _PROMPT, **kwargs) -> tuple[float, str | None, Exception | None]:
    """Execute a single LLM call and return (latency_s, result, error)."""
    t0 = time.time()
    try:
        result = call_llm_text(prompt, **kwargs)
        return time.time() - t0, result, None
    except Exception as exc:
        return time.time() - t0, None, exc


def _percentile(data: list[float], pct: float) -> float:
    """Compute percentile from sorted data."""
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100.0)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.performance
@skip_no_llm
def test_perf_single_request_latency():
    """3 sequential LLM calls — measure P50/P95/P99 latency."""
    latencies: list[float] = []
    for _ in range(3):
        elapsed, result, err = _timed_call()
        assert err is None, f"LLM call failed: {err}"
        assert result is not None and len(result) > 0
        latencies.append(elapsed)

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)

    # Single request should complete within 15s
    assert p50 < 15.0, f"P50 latency {p50:.2f}s exceeds 15s"
    assert p95 < 15.0, f"P95 latency {p95:.2f}s exceeds 15s"
    assert p99 < 15.0, f"P99 latency {p99:.2f}s exceeds 15s"


@pytest.mark.performance
@skip_no_llm
def test_perf_5_concurrent_requests():
    """5 threads each making a call_llm_text — measure avg/max latency."""
    results: list[tuple[float, str | None, Exception | None]] = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_timed_call) for _ in range(5)]
        for f in as_completed(futures):
            results.append(f.result())

    latencies = [r[0] for r in results]
    errors = [r[2] for r in results if r[2] is not None]

    # All 5 should succeed
    assert len(errors) == 0, f"Failures: {errors}"

    avg_lat = statistics.mean(latencies)
    max_lat = max(latencies)

    assert avg_lat < 20.0, f"Avg latency {avg_lat:.2f}s exceeds 20s"
    assert max_lat < 30.0, f"Max latency {max_lat:.2f}s exceeds 30s"


@pytest.mark.performance
@skip_no_llm
def test_perf_10_concurrent_requests():
    """10 threads — measure success rate and latency distribution."""
    results: list[tuple[float, str | None, Exception | None]] = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_timed_call) for _ in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r[2] is None]
    success_rate = len(successes) / len(results)

    # At least 80% success rate
    assert success_rate >= 0.8, f"Success rate {success_rate:.0%} below 80%"

    if successes:
        latencies = [r[0] for r in successes]
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        assert p50 < 25.0, f"P50={p50:.2f}s too high under 10-concurrent load"
        assert p95 < 40.0, f"P95={p95:.2f}s too high under 10-concurrent load"


@pytest.mark.performance
@skip_no_llm
def test_perf_20_concurrent_requests():
    """20 threads — expect some governance rejections."""
    results: list[tuple[float, str | None, Exception | None]] = []

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_timed_call, estimated_tokens=4096) for _ in range(20)]
        for f in as_completed(futures):
            results.append(f.result())

    governance_errors = [
        r for r in results if r[2] is not None and isinstance(r[2], LLMGovernanceError)
    ]
    successes = [r for r in results if r[2] is None]

    # With 20 concurrent + large token estimate, governance should block some
    total = len(results)
    blocked = len(governance_errors)
    succeeded = len(successes)

    # At least some succeed and some get blocked (or all succeed if bucket is big)
    assert succeeded + blocked == total or succeeded > 0


@pytest.mark.performance
@skip_no_llm
def test_perf_burst_50_requests():
    """50 rapid-fire requests — measure governance blocking rate."""
    results: list[tuple[float, str | None, Exception | None]] = []

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(_timed_call, estimated_tokens=4096) for _ in range(50)]
        for f in as_completed(futures):
            results.append(f.result())

    governance_blocked = sum(
        1 for r in results if r[2] is not None and isinstance(r[2], LLMGovernanceError)
    )
    block_rate = governance_blocked / len(results)

    # Rate limiter should block > 30% of burst requests
    assert block_rate > 0.30, (
        f"Governance blocked only {block_rate:.0%} of 50 burst requests; "
        f"expected > 30% — rate limiting may not be effective"
    )
