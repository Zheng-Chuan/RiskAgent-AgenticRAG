"""LLM Cost Governance -- Token Bucket rate limiter for LLM API calls.

Provides per-priority token bucket rate limiting to prevent excessive LLM
token consumption. Integrates with Prometheus metrics for observability.
"""

from __future__ import annotations

import logging
import threading
import time

from prometheus_client import Counter, Gauge

from riskagent_agenticrag.config.settings import get_settings

__all__ = [
    "TokenBucket",
    "LLMCostGovernor",
    "LLMGovernanceError",
    "get_llm_cost_governor",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

_rate_limited_counter = Counter(
    "riskagent_llm_rate_limited_total",
    "Total number of LLM requests rejected by rate limiter",
    ["priority"],
)

_tokens_available_gauge = Gauge(
    "riskagent_llm_rate_limit_tokens_available",
    "Current available tokens in the rate limiter bucket",
    ["priority"],
)


# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------


class LLMGovernanceError(Exception):
    """Raised when the LLM governance layer blocks a request."""

    def __init__(self, metadata: dict):
        self.metadata = metadata
        super().__init__(f"LLM governance blocked: {metadata}")


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------


class TokenBucket:
    """Thread-safe token bucket rate limiter.

    Tokens are refilled at a constant rate up to the bucket capacity.
    Consumers attempt to withdraw tokens; if insufficient tokens are
    available the request is rejected.
    """

    def __init__(self, capacity: float, refill_per_second: float) -> None:
        """Initialize the token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_per_second: Rate at which tokens are added per second.
        """
        self._capacity = float(max(0.0, capacity))
        self._refill_per_second = float(max(0.0, refill_per_second))
        self._tokens = self._capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time (must be called under lock)."""
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_refill)
        if elapsed > 0.0 and self._refill_per_second > 0.0:
            self._tokens = min(
                self._capacity, self._tokens + elapsed * self._refill_per_second
            )
        self._last_refill = now

    def consume(self, tokens: float) -> bool:
        """Attempt to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were successfully consumed, False otherwise.
        """
        amount = float(max(0.0, tokens))
        if amount <= 0.0:
            return True

        with self._lock:
            self._refill()
            if amount > self._capacity:
                return False
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    @property
    def available(self) -> float:
        """Return the current number of available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    @property
    def capacity(self) -> float:
        """Return the bucket capacity."""
        return self._capacity

    def time_until_available(self, tokens: float) -> float:
        """Estimate seconds until the requested tokens become available.

        Args:
            tokens: Number of tokens needed.

        Returns:
            Estimated wait time in seconds; 0.0 if tokens are available now.
        """
        amount = float(max(0.0, tokens))
        with self._lock:
            self._refill()
            if self._tokens >= amount:
                return 0.0
            if self._refill_per_second <= 0.0:
                return float("inf")
            deficit = amount - self._tokens
            return deficit / self._refill_per_second


# ---------------------------------------------------------------------------
# LLM Cost Governor
# ---------------------------------------------------------------------------

# Priority alias mapping
_PRIORITY_ALIASES: dict[str, str] = {
    "noncritical": "non_critical",
    "query": "non_critical",
}


class LLMCostGovernor:
    """Rate-limiting governor for LLM API token consumption.

    Creates per-priority token buckets based on project configuration.
    Integrates with Prometheus metrics for real-time observability.
    """

    def __init__(self) -> None:
        """Initialize the governor with per-priority token buckets from settings."""
        cfg = get_settings().llm_governance
        self._buckets: dict[str, TokenBucket] = {}

        # Default priority bucket
        default_capacity = (
            cfg.burst_tokens if cfg.burst_tokens > 0 else cfg.rate_limit_tokens_per_min
        )
        default_refill = cfg.rate_limit_tokens_per_min / 60.0
        self._rate_limit_tokens_per_min_default = cfg.rate_limit_tokens_per_min

        if cfg.rate_limit_tokens_per_min > 0:
            self._buckets["default"] = TokenBucket(
                capacity=float(default_capacity),
                refill_per_second=default_refill,
            )

        # Non-critical priority bucket
        nc_capacity = (
            cfg.burst_tokens_non_critical
            if cfg.burst_tokens_non_critical > 0
            else cfg.rate_limit_tokens_per_min_non_critical
        )
        nc_refill = cfg.rate_limit_tokens_per_min_non_critical / 60.0
        self._rate_limit_tokens_per_min_non_critical = (
            cfg.rate_limit_tokens_per_min_non_critical
        )

        if cfg.rate_limit_tokens_per_min_non_critical > 0:
            self._buckets["non_critical"] = TokenBucket(
                capacity=float(nc_capacity),
                refill_per_second=nc_refill,
            )

        logger.info(
            "LLMCostGovernor initialized: default=%d tpm, non_critical=%d tpm",
            cfg.rate_limit_tokens_per_min,
            cfg.rate_limit_tokens_per_min_non_critical,
        )

    def _resolve_priority(self, priority: str) -> str:
        """Resolve priority aliases to canonical names."""
        key = (priority or "default").strip().lower()
        return _PRIORITY_ALIASES.get(key, key)

    def allow(
        self, priority: str = "default", estimated_tokens: int = 0
    ) -> tuple[bool, dict]:
        """Check whether a request is allowed under the current rate limits.

        Args:
            priority: The priority tier for the request (e.g. "default",
                "non_critical", "noncritical", "query").
            estimated_tokens: Estimated number of tokens the request will consume.

        Returns:
            A tuple of (allowed, metadata). If allowed is True, metadata contains
            priority and tokens_available. If False, metadata contains reason,
            priority, and retry_after_s.
        """
        resolved = self._resolve_priority(priority)

        # If no bucket configured for this priority, governor is disabled
        bucket = self._buckets.get(resolved)
        if bucket is None:
            return True, {"priority": resolved, "tokens_available": float("inf")}

        tokens_needed = float(max(0, int(estimated_tokens)))
        ok = bucket.consume(tokens_needed)

        # Update Prometheus gauge
        available = bucket.available
        _tokens_available_gauge.labels(priority=resolved).set(available)

        if ok:
            return True, {"priority": resolved, "tokens_available": available}

        # Request rejected
        retry_after = bucket.time_until_available(tokens_needed)
        _rate_limited_counter.labels(priority=resolved).inc()

        logger.warning(
            "LLM rate limited: priority=%s, requested=%d, available=%.1f, retry_after=%.2fs",
            resolved,
            estimated_tokens,
            available,
            retry_after,
        )

        return False, {
            "reason": "rate_limited",
            "priority": resolved,
            "retry_after_s": retry_after,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_governor: LLMCostGovernor | None = None


def get_llm_cost_governor() -> LLMCostGovernor:
    """Get or create the module-level LLMCostGovernor singleton.

    Returns:
        The shared LLMCostGovernor instance.
    """
    global _governor  # noqa: PLW0603
    if _governor is None:
        _governor = LLMCostGovernor()
    return _governor
