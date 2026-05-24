"""
Integration tests for LLM Traffic Management (governance, token_tracker, llm_cache, generate).

Prerequisites:
    1. Docker services running: make up
    2. Conda environment activated: conda activate riskagent-agenticrag
    3. .env file with valid LLM_API_KEY / OPENAI_API_KEY

Run:
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_integration_llm_governance.py -v -s
"""

from __future__ import annotations

import os
import socket
import threading
import time
import unittest

import pytest
import requests

# ---------------------------------------------------------------------------
# Infrastructure availability checks
# ---------------------------------------------------------------------------


def _redis_available() -> bool:
    """Check if Redis is reachable at localhost:6379."""
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, password="riskagent", db=0, socket_timeout=3)
        return r.ping()
    except Exception:
        return False


def _milvus_available() -> bool:
    """Check if Milvus is reachable at localhost:19530."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            return sock.connect_ex(("127.0.0.1", 19530)) == 0
    except Exception:
        return False


def _llm_api_key_present() -> bool:
    """Check if LLM API key is available in environment."""
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"))


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration


# ===========================================================================
# Class 1: TestRealInfrastructureConnectivity
# ===========================================================================


@pytest.mark.integration
class TestRealInfrastructureConnectivity(unittest.TestCase):
    """Verify real Docker middleware and LLM API are reachable."""

    @classmethod
    def setUpClass(cls) -> None:
        # Minimal sanity: at least API key should be present
        if not _llm_api_key_present():
            raise unittest.SkipTest("LLM API key not configured; skipping infrastructure tests")

    def test_redis_connection(self) -> None:
        """Connect to Redis, PING, set/get a test key."""
        import redis

        r = redis.Redis(host="localhost", port=6379, password="riskagent", db=0, socket_timeout=5)
        self.assertTrue(r.ping(), "Redis PING failed")

        test_key = "test:integration:llm_governance"
        r.set(test_key, "hello_integration")
        val = r.get(test_key)
        self.assertEqual(val, b"hello_integration")
        r.delete(test_key)
        print(f"  [OK] Redis connected and set/get verified")

    def test_milvus_connection(self) -> None:
        """Socket connect to port 19530, and HTTP healthz on 9091."""
        # TCP check
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            result = sock.connect_ex(("127.0.0.1", 19530))
            self.assertEqual(result, 0, "Milvus TCP port 19530 not reachable")
        print(f"  [OK] Milvus TCP:19530 reachable")

        # HTTP healthz
        try:
            resp = requests.get("http://localhost:9091/healthz", timeout=5)
            self.assertEqual(resp.status_code, 200)
            print(f"  [OK] Milvus healthz HTTP 200")
        except requests.ConnectionError:
            self.skipTest("Milvus healthz endpoint not reachable at :9091")

    @unittest.skipUnless(_llm_api_key_present(), "No LLM API key configured")
    def test_llm_api_reachable(self) -> None:
        """Make a minimal real LLM call (say hello) and verify response."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        reset_token_tracker()
        response = call_llm_text("Say hello in one word.", temperature=0.0)
        self.assertTrue(len(response.strip()) > 0, "LLM returned empty response")
        print(f"  [OK] LLM API responded: {response[:80]!r}")


# ===========================================================================
# Class 2: TestTokenBucketReal
# ===========================================================================


@pytest.mark.integration
class TestTokenBucketReal(unittest.TestCase):
    """Test TokenBucket and LLMCostGovernor with real instances."""

    def test_bucket_allows_within_capacity(self) -> None:
        """Create a TokenBucket, consume tokens within capacity, verify allowed."""
        from riskagent_agenticrag.llm.governance import TokenBucket

        bucket = TokenBucket(capacity=1000.0, refill_per_second=100.0)
        self.assertTrue(bucket.consume(500))
        self.assertAlmostEqual(bucket.available, 500.0, delta=10.0)
        print(f"  [OK] Bucket consumed 500/1000, available={bucket.available:.1f}")

    def test_bucket_rejects_over_capacity(self) -> None:
        """Consume all tokens, verify next consume is rejected."""
        from riskagent_agenticrag.llm.governance import TokenBucket

        bucket = TokenBucket(capacity=100.0, refill_per_second=1.0)
        self.assertTrue(bucket.consume(100))
        self.assertFalse(bucket.consume(50))
        print(f"  [OK] Bucket correctly rejected over-capacity request")

    def test_bucket_refills_over_time(self) -> None:
        """Consume all, sleep briefly, verify partial refill allows smaller request."""
        from riskagent_agenticrag.llm.governance import TokenBucket

        bucket = TokenBucket(capacity=100.0, refill_per_second=100.0)
        self.assertTrue(bucket.consume(100))
        # Sleep 0.5s -> refill ~50 tokens
        time.sleep(0.5)
        available = bucket.available
        self.assertGreater(available, 30.0)  # at least 30 tokens refilled
        self.assertTrue(bucket.consume(30))
        print(f"  [OK] Bucket refilled to {available:.1f} after 0.5s sleep")

    def test_governor_allows_default_priority(self) -> None:
        """Use get_llm_cost_governor(), call allow('default', 1000), verify allowed."""
        from riskagent_agenticrag.llm import governance

        # Reset singleton to get fresh governor
        governance._governor = None
        governor = governance.get_llm_cost_governor()
        allowed, meta = governor.allow("default", 1000)
        self.assertTrue(allowed)
        self.assertEqual(meta["priority"], "default")
        print(f"  [OK] Governor allowed default priority, meta={meta}")

    def test_governor_respects_non_critical_limit(self) -> None:
        """Exhaust non_critical bucket, verify rejection."""
        from riskagent_agenticrag.llm.governance import LLMCostGovernor, TokenBucket

        # Create a fresh governor with small non_critical bucket
        governor = LLMCostGovernor.__new__(LLMCostGovernor)
        governor._buckets = {
            "default": TokenBucket(capacity=100000.0, refill_per_second=1000.0),
            "non_critical": TokenBucket(capacity=100.0, refill_per_second=0.1),
        }
        governor._rate_limit_tokens_per_min_default = 60000
        governor._rate_limit_tokens_per_min_non_critical = 6

        # Exhaust non_critical
        allowed, _ = governor.allow("non_critical", 100)
        self.assertTrue(allowed)

        # Next request should be rejected
        allowed, meta = governor.allow("non_critical", 50)
        self.assertFalse(allowed)
        self.assertEqual(meta["reason"], "rate_limited")
        print(f"  [OK] Governor rejected non_critical after exhaustion, meta={meta}")


# ===========================================================================
# Class 3: TestTokenTrackerReal
# ===========================================================================


@pytest.mark.integration
@unittest.skipUnless(_llm_api_key_present(), "No LLM API key configured")
class TestTokenTrackerReal(unittest.TestCase):
    """Test TokenTracker with real LLM calls."""

    @classmethod
    def setUpClass(cls) -> None:
        if not _llm_api_key_present():
            raise unittest.SkipTest("No LLM API key configured")
        # Reset singletons
        from riskagent_agenticrag.llm import governance
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        reset_token_tracker()
        governance._governor = None

    def setUp(self) -> None:
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        reset_token_tracker()
        # Also reset cache to avoid cache hits affecting token tracking
        from riskagent_agenticrag.llm import llm_cache

        llm_cache._cache = None

    def test_record_real_llm_call(self) -> None:
        """Make a REAL LLM call via call_llm_text(), then check get_token_tracker().get_usage() shows >0 tokens."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        call_llm_text("What is 2+2? Answer in one word.", temperature=0.7)
        usage = get_token_tracker().get_usage()
        self.assertGreater(usage["total_tokens"], 0)
        self.assertGreater(usage["calls"], 0)
        print(f"  [OK] Token tracker recorded: {usage['total_tokens']} tokens, {usage['calls']} calls")

    def test_usage_aggregation(self) -> None:
        """Make 3 real LLM calls, verify get_usage() shows calls==3 and tokens increasing."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        # Reset cache to ensure all 3 calls hit the LLM
        from riskagent_agenticrag.llm import llm_cache

        llm_cache._cache = None

        prompts = [
            "Name one color.",
            "Name one fruit.",
            "Name one animal.",
        ]
        for p in prompts:
            call_llm_text(p, temperature=0.7)

        usage = get_token_tracker().get_usage()
        self.assertEqual(usage["calls"], 3)
        self.assertGreater(usage["total_tokens"], 0)
        print(f"  [OK] Aggregation: calls={usage['calls']}, total_tokens={usage['total_tokens']}")

    def test_usage_by_model(self) -> None:
        """Verify get_usage()['by_model'] contains the configured model name."""
        from riskagent_agenticrag.config.settings import get_settings
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        model_name = get_settings().llm.model
        call_llm_text("Say yes.", temperature=0.7)
        usage = get_token_tracker().get_usage()
        by_model = usage["by_model"]
        self.assertIn(model_name, by_model)
        model_stats = by_model[model_name]
        self.assertGreater(model_stats["total_tokens"], 0)
        self.assertEqual(model_stats["calls"], 1)
        print(f"  [OK] by_model contains {model_name}: {model_stats}")

    def test_alert_thresholds_in_usage(self) -> None:
        """Verify get_usage() returns correct alert threshold values from config."""
        from riskagent_agenticrag.config.settings import get_settings
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        cfg = get_settings().llm_governance
        usage = get_token_tracker().get_usage()
        self.assertEqual(usage["alert_threshold_hourly"], cfg.token_alert_hourly)
        self.assertEqual(usage["alert_threshold_daily"], cfg.token_alert_daily)
        print(
            f"  [OK] Alert thresholds: hourly={usage['alert_threshold_hourly']}, "
            f"daily={usage['alert_threshold_daily']}"
        )


# ===========================================================================
# Class 4: TestLLMCacheReal
# ===========================================================================


@pytest.mark.integration
@unittest.skipUnless(_llm_api_key_present(), "No LLM API key configured")
class TestLLMCacheReal(unittest.TestCase):
    """Test LLMCache with real LLM calls."""

    @classmethod
    def setUpClass(cls) -> None:
        if not _llm_api_key_present():
            raise unittest.SkipTest("No LLM API key configured")

    def setUp(self) -> None:
        from riskagent_agenticrag.llm import llm_cache
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        # Reset cache singleton
        llm_cache._cache = None
        reset_token_tracker()
        # Reset governor
        from riskagent_agenticrag.llm import governance

        governance._governor = None

    def test_cache_miss_on_first_call(self) -> None:
        """Make a real LLM call with temperature=0.0, verify it's a cache miss."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.llm_cache import get_llm_cache
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        prompt = "Define the word 'cache' in one sentence."
        t0 = time.time()
        result = call_llm_text(prompt, temperature=0.0)
        latency_first = time.time() - t0

        self.assertTrue(len(result.strip()) > 0)
        # Cache should now have 1 entry
        cache = get_llm_cache()
        self.assertEqual(cache.size(), 1)
        print(f"  [OK] Cache miss on first call, latency={latency_first:.2f}s, response={result[:60]!r}")

    def test_cache_hit_on_repeated_call(self) -> None:
        """Make the SAME call again with temperature=0.0, verify cache hit (faster response)."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        prompt = "What is the capital of France? One word answer."
        # First call - cache miss
        t0 = time.time()
        result1 = call_llm_text(prompt, temperature=0.0)
        latency_first = time.time() - t0

        # Reset tracker to isolate second call stats
        tracker = get_token_tracker()
        tracker.reset()

        # Second call - should be cache hit
        t1 = time.time()
        result2 = call_llm_text(prompt, temperature=0.0)
        latency_second = time.time() - t1

        # Cache hit should be much faster (no network call)
        self.assertLess(latency_second, latency_first)
        self.assertLess(latency_second, 0.1)  # Cache hit should be < 100ms

        # Tracker should show cached=True
        usage = tracker.get_usage()
        self.assertEqual(usage["calls"], 1)  # cached call still recorded
        print(
            f"  [OK] Cache hit: first={latency_first:.2f}s, second={latency_second:.4f}s, "
            f"response={result2[:60]!r}"
        )

    def test_cache_bypass_for_non_deterministic(self) -> None:
        """Make a call with temperature=0.7, verify it's never cached."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.llm_cache import get_llm_cache

        prompt = "Give me a random number between 1 and 100."
        call_llm_text(prompt, temperature=0.7)
        call_llm_text(prompt, temperature=0.7)

        # Cache should remain empty for non-deterministic calls
        cache = get_llm_cache()
        self.assertEqual(cache.size(), 0)
        print(f"  [OK] Non-deterministic calls (temp=0.7) not cached, cache size={cache.size()}")

    def test_cache_eviction(self) -> None:
        """Use small cache_max_size override, fill cache, add one more, verify oldest evicted."""
        from riskagent_agenticrag.llm.llm_cache import CachedResponse, LLMCache

        # Create a small cache (max_size=2)
        cache = LLMCache(max_size=2)

        # Fill with 2 entries
        cache.put("key1", CachedResponse(
            content="resp1", prompt_tokens=10, completion_tokens=5, model="test", cached_at=time.time()
        ))
        cache.put("key2", CachedResponse(
            content="resp2", prompt_tokens=10, completion_tokens=5, model="test", cached_at=time.time()
        ))
        self.assertEqual(cache.size(), 2)

        # Add a third - should evict key1
        cache.put("key3", CachedResponse(
            content="resp3", prompt_tokens=10, completion_tokens=5, model="test", cached_at=time.time()
        ))
        self.assertEqual(cache.size(), 2)
        self.assertIsNone(cache.get("key1"))  # evicted
        self.assertIsNotNone(cache.get("key2"))
        self.assertIsNotNone(cache.get("key3"))
        print(f"  [OK] Cache eviction working: key1 evicted, key2 & key3 retained")


# ===========================================================================
# Class 5: TestGenerateIntegrationReal
# ===========================================================================


@pytest.mark.integration
@unittest.skipUnless(_llm_api_key_present(), "No LLM API key configured")
class TestGenerateIntegrationReal(unittest.TestCase):
    """Test generate module with real LLM calls."""

    @classmethod
    def setUpClass(cls) -> None:
        if not _llm_api_key_present():
            raise unittest.SkipTest("No LLM API key configured")

    def setUp(self) -> None:
        from riskagent_agenticrag.llm import governance, llm_cache
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        reset_token_tracker()
        llm_cache._cache = None
        governance._governor = None

    def test_call_llm_text_real(self) -> None:
        """Call call_llm_text('What is FRTB in one sentence?') with real LLM, verify non-empty string."""
        from riskagent_agenticrag.llm.generate import call_llm_text

        response = call_llm_text("What is FRTB in one sentence?", temperature=0.0)
        self.assertIsInstance(response, str)
        self.assertTrue(len(response.strip()) > 10)
        print(f"  [OK] Real LLM response: {response[:100]!r}")

    def test_call_llm_text_with_governance(self) -> None:
        """Verify governance allows normal calls (call succeeds)."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.governance import get_llm_cost_governor

        governor = get_llm_cost_governor()
        # Verify governor is active
        allowed, meta = governor.allow("default", 100)
        self.assertTrue(allowed)

        # Make a real call through governance
        response = call_llm_text("Say OK.", temperature=0.7)
        self.assertTrue(len(response.strip()) > 0)
        print(f"  [OK] Governance-gated call succeeded: {response[:50]!r}")

    def test_call_llm_text_records_tokens(self) -> None:
        """After call, verify token_tracker has recorded usage."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        call_llm_text("What is Basel III?", temperature=0.7)
        usage = get_token_tracker().get_usage()
        self.assertGreater(usage["total_tokens"], 0)
        self.assertEqual(usage["calls"], 1)
        print(f"  [OK] Token tracker recorded: tokens={usage['total_tokens']}, calls={usage['calls']}")

    def test_call_llm_text_caches_deterministic(self) -> None:
        """Call with temperature=0.0 twice, verify second is faster (cached)."""
        from riskagent_agenticrag.llm.generate import call_llm_text

        prompt = "What is VaR in one sentence?"
        t0 = time.time()
        r1 = call_llm_text(prompt, temperature=0.0)
        latency1 = time.time() - t0

        t1 = time.time()
        r2 = call_llm_text(prompt, temperature=0.0)
        latency2 = time.time() - t1

        self.assertLess(latency2, 0.1)  # cached should be instant
        self.assertEqual(r1, r2)  # same content from cache
        print(f"  [OK] Caching works: first={latency1:.2f}s, cached={latency2:.4f}s")

    def test_call_llm_text_retry_on_transient_error(self) -> None:
        """Simulate one transient failure, then real call succeeds on retry."""
        from unittest.mock import patch

        from riskagent_agenticrag.llm.generate import call_llm_text

        call_count = {"n": 0}

        # Import the real function
        from riskagent_agenticrag.llm import generate

        original_fn = generate._call_via_langchain

        def patched_langchain(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("Simulated transient network error")
            return original_fn(*args, **kwargs)

        with patch.object(generate, "_call_via_langchain", side_effect=patched_langchain):
            response = call_llm_text("Say retry-ok.", temperature=0.7)

        self.assertTrue(len(response.strip()) > 0)
        self.assertEqual(call_count["n"], 2)  # first failed, second succeeded
        print(f"  [OK] Retry succeeded after transient error: {response[:50]!r}")

    def test_governance_blocks_when_exhausted(self) -> None:
        """Create a governor with very low capacity (1 token), verify LLMGovernanceError."""
        from riskagent_agenticrag.llm import governance
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.governance import (
            LLMCostGovernor,
            LLMGovernanceError,
            TokenBucket,
        )

        # Create exhausted governor
        tiny_governor = LLMCostGovernor.__new__(LLMCostGovernor)
        tiny_governor._buckets = {
            "default": TokenBucket(capacity=1.0, refill_per_second=0.001),
        }
        tiny_governor._rate_limit_tokens_per_min_default = 1
        tiny_governor._rate_limit_tokens_per_min_non_critical = 0

        # Exhaust the single token
        tiny_governor._buckets["default"].consume(1.0)

        # Patch singleton
        old_governor = governance._governor
        governance._governor = tiny_governor
        try:
            with self.assertRaises(LLMGovernanceError) as ctx:
                call_llm_text("This should be blocked.", temperature=0.0)
            self.assertIn("rate_limited", str(ctx.exception.metadata))
            print(f"  [OK] Governance blocked exhausted request: {ctx.exception.metadata}")
        finally:
            governance._governor = old_governor


# ===========================================================================
# Class 6: TestEndToEndFlow
# ===========================================================================


@pytest.mark.integration
@unittest.skipUnless(_llm_api_key_present(), "No LLM API key configured")
class TestEndToEndFlow(unittest.TestCase):
    """End-to-end pipeline tests with real LLM calls."""

    @classmethod
    def setUpClass(cls) -> None:
        if not _llm_api_key_present():
            raise unittest.SkipTest("No LLM API key configured")

    def setUp(self) -> None:
        from riskagent_agenticrag.llm import governance, llm_cache
        from riskagent_agenticrag.llm.token_tracker import reset_token_tracker

        reset_token_tracker()
        llm_cache._cache = None
        governance._governor = None

    def test_full_pipeline_real_llm(self) -> None:
        """Make a real call through full pipeline, verify all components recorded correctly."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.governance import get_llm_cost_governor
        from riskagent_agenticrag.llm.llm_cache import get_llm_cache
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        prompt = "Explain market risk in one sentence."

        # Execute full pipeline
        response = call_llm_text(prompt, temperature=0.0)

        # Verify response
        self.assertTrue(len(response.strip()) > 10)

        # Verify token tracker recorded
        usage = get_token_tracker().get_usage()
        self.assertEqual(usage["calls"], 1)
        self.assertGreater(usage["total_tokens"], 0)

        # Verify cache stored (deterministic call)
        cache = get_llm_cache()
        self.assertEqual(cache.size(), 1)

        # Verify governor still has capacity
        governor = get_llm_cost_governor()
        allowed, _ = governor.allow("default", 100)
        self.assertTrue(allowed)

        print(
            f"  [OK] Full pipeline: response={response[:60]!r}, "
            f"tokens={usage['total_tokens']}, cache_size={cache.size()}"
        )

    def test_multiple_sequential_calls(self) -> None:
        """Make 5 sequential real LLM calls, verify token tracker shows 5 calls."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        prompts = [
            "Name a European country.",
            "Name an Asian country.",
            "Name a South American country.",
            "Name an African country.",
            "Name an Oceanian country.",
        ]

        total_tokens_prev = 0
        for i, prompt in enumerate(prompts, 1):
            call_llm_text(prompt, temperature=0.7)
            usage = get_token_tracker().get_usage()
            self.assertEqual(usage["calls"], i)
            self.assertGreater(usage["total_tokens"], total_tokens_prev)
            total_tokens_prev = usage["total_tokens"]

        final_usage = get_token_tracker().get_usage()
        self.assertEqual(final_usage["calls"], 5)
        print(
            f"  [OK] 5 sequential calls: total_tokens={final_usage['total_tokens']}, "
            f"calls={final_usage['calls']}"
        )

    def test_concurrent_calls_thread_safety(self) -> None:
        """Spawn 3 threads each making a real LLM call, verify all succeed and tracker shows 3 calls."""
        from riskagent_agenticrag.llm.generate import call_llm_text
        from riskagent_agenticrag.llm.token_tracker import get_token_tracker

        results: list[str | None] = [None, None, None]
        errors: list[Exception | None] = [None, None, None]

        def worker(idx: int, prompt: str) -> None:
            try:
                results[idx] = call_llm_text(prompt, temperature=0.7)
            except Exception as e:
                errors[idx] = e

        threads = [
            threading.Thread(target=worker, args=(0, "Name a primary color.")),
            threading.Thread(target=worker, args=(1, "Name a planet.")),
            threading.Thread(target=worker, args=(2, "Name a programming language.")),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # Verify no errors
        for i, err in enumerate(errors):
            self.assertIsNone(err, f"Thread {i} raised: {err}")

        # Verify all responses
        for i, result in enumerate(results):
            self.assertIsNotNone(result, f"Thread {i} returned None")
            self.assertTrue(len(result.strip()) > 0, f"Thread {i} returned empty")

        # Verify tracker
        usage = get_token_tracker().get_usage()
        self.assertEqual(usage["calls"], 3)
        self.assertGreater(usage["total_tokens"], 0)
        print(
            f"  [OK] 3 concurrent calls: results={[r[:20] for r in results]}, "
            f"tokens={usage['total_tokens']}"
        )


if __name__ == "__main__":
    unittest.main()
