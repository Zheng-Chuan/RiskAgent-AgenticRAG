"""LLM Token 用量追踪与告警模块.

职责:
- 记录每次 LLM 调用的真实 token 消耗到 Prometheus 指标
- 维护滑动窗口（小时 + 日）累计统计
- 超过阈值时触发告警（仅告警不阻断）
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from prometheus_client import Counter, Gauge, Histogram

from riskagent_agenticrag.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------- #
# Prometheus metrics
# ---------------------------------------------------------------------- #
_PROMPT_TOKENS = Counter(
    "riskagent_llm_prompt_tokens_total",
    "Total prompt tokens consumed",
    ["model"],
)

_COMPLETION_TOKENS = Counter(
    "riskagent_llm_completion_tokens_total",
    "Total completion tokens consumed",
    ["model"],
)

_CALLS = Counter(
    "riskagent_llm_calls_total",
    "Total LLM calls",
    ["model", "cached"],
)

_LATENCY = Histogram(
    "riskagent_llm_latency_seconds",
    "LLM call latency in seconds",
    ["model"],
)

_TOKENS_LAST_HOUR = Gauge(
    "riskagent_llm_tokens_used_last_hour",
    "Total tokens consumed in the last hour (sliding window)",
)

_ALERT_FIRED = Counter(
    "riskagent_llm_token_alert_fired_total",
    "Number of token alert events fired",
    ["level"],
)


# ---------------------------------------------------------------------- #
# Internal record type
# ---------------------------------------------------------------------- #
@dataclass
class TokenUsageRecord:
    """Single LLM call token usage record."""

    timestamp: float
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float = 0.0
    cached: bool = False


# ---------------------------------------------------------------------- #
# Tracker
# ---------------------------------------------------------------------- #
class TokenTracker:
    """LLM Token usage tracker.

    - Thread-safe via :class:`threading.Lock`
    - Sliding-window aggregation for hourly (3600 s) and daily (86400 s)
    - Fires log WARNING + Prometheus counter when thresholds are exceeded;
      never raises exceptions or blocks callers.
    """

    def __init__(self, window_s: int = 3600, daily_window_s: int = 86400) -> None:
        self._window_s = int(window_s) if window_s and window_s > 0 else 3600
        self._daily_window_s = (
            int(daily_window_s) if daily_window_s and daily_window_s > 0 else 86400
        )

        cfg = settings.llm_governance
        self._hourly_threshold: int = int(cfg.token_alert_hourly)
        self._daily_threshold: int = int(cfg.token_alert_daily)

        self._lock: threading.Lock = threading.Lock()
        self._records: deque[TokenUsageRecord] = deque()
        self._daily_records: deque[TokenUsageRecord] = deque()

        self._hourly_alert_triggered: bool = False
        self._daily_alert_triggered: bool = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float = 0.0,
        cached: bool = False,
    ) -> None:
        """Record one LLM call's token usage.

        Args:
            model: Model identifier string.
            prompt_tokens: Number of input/prompt tokens.
            completion_tokens: Number of output/completion tokens.
            latency_ms: End-to-end call latency in milliseconds.
            cached: Whether the response was served from cache.
        """
        try:
            model_str = str(model) if model is not None else "unknown"
            p_tokens = _safe_int(prompt_tokens)
            c_tokens = _safe_int(completion_tokens)
            t_tokens = p_tokens + c_tokens
            latency = _safe_float(latency_ms)
            cached_bool = bool(cached)
            cached_label = "true" if cached_bool else "false"

            # 1) Prometheus counters
            try:
                if p_tokens > 0:
                    _PROMPT_TOKENS.labels(model=model_str).inc(p_tokens)
                if c_tokens > 0:
                    _COMPLETION_TOKENS.labels(model=model_str).inc(c_tokens)
                _CALLS.labels(model=model_str, cached=cached_label).inc()
            except Exception:  # pragma: no cover
                logger.debug("Prometheus counter update failed in token_tracker", exc_info=True)

            # 2) Latency histogram (convert ms → seconds)
            if latency > 0:
                try:
                    _LATENCY.labels(model=model_str).observe(latency / 1000.0)
                except Exception:  # pragma: no cover
                    logger.debug("Prometheus histogram update failed in token_tracker", exc_info=True)

            # 3) Structured log
            logger.info(
                "llm_token_usage model=%s prompt=%d completion=%d total=%d "
                "latency_ms=%.2f cached=%s",
                model_str,
                p_tokens,
                c_tokens,
                t_tokens,
                latency,
                cached_bool,
            )

            # 4) Sliding-window deques
            now = time.time()
            rec = TokenUsageRecord(
                timestamp=now,
                model=model_str,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
                latency_ms=latency,
                cached=cached_bool,
            )

            with self._lock:
                self._records.append(rec)
                self._daily_records.append(rec)
                self._cleanup_locked(now)

                # 5) Gauge: tokens in last hour
                hourly_total = sum(r.total_tokens for r in self._records)
                try:
                    _TOKENS_LAST_HOUR.set(float(hourly_total))
                except Exception:  # pragma: no cover
                    logger.debug("Prometheus gauge update failed in token_tracker", exc_info=True)

                # 6) Alert checks
                self._check_alerts_locked()

        except Exception:  # pragma: no cover - never block caller
            logger.warning("TokenTracker.record failed", exc_info=True)

    def get_usage(self) -> dict[str, Any]:
        """Return aggregated usage statistics for current windows.

        Returns:
            Dictionary with hourly and daily window statistics, per-model
            breakdown, configured thresholds, and alert trigger flags.
        """
        with self._lock:
            self._cleanup_locked(time.time())
            records = list(self._records)
            daily_records = list(self._daily_records)
            hourly_alert = self._hourly_alert_triggered
            daily_alert = self._daily_alert_triggered

        total_tokens = sum(r.total_tokens for r in records)
        prompt_tokens = sum(r.prompt_tokens for r in records)
        completion_tokens = sum(r.completion_tokens for r in records)
        calls = len(records)

        by_model: dict[str, dict[str, int]] = {}
        for r in records:
            entry = by_model.setdefault(
                r.model,
                {
                    "total_tokens": 0,
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                },
            )
            entry["total_tokens"] += r.total_tokens
            entry["calls"] += 1
            entry["prompt_tokens"] += r.prompt_tokens
            entry["completion_tokens"] += r.completion_tokens

        daily_total = sum(r.total_tokens for r in daily_records)

        return {
            "window_hours": max(1, self._window_s // 3600),
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "calls": calls,
            "by_model": by_model,
            "alert_threshold_hourly": self._hourly_threshold,
            "alert_threshold_daily": self._daily_threshold,
            "hourly_alert_triggered": bool(hourly_alert),
            "daily_alert_triggered": bool(daily_alert),
            "daily_total_tokens": daily_total,
        }

    def reset(self) -> None:
        """Reset all internal state (intended for testing only)."""
        with self._lock:
            self._records.clear()
            self._daily_records.clear()
            self._hourly_alert_triggered = False
            self._daily_alert_triggered = False
        try:
            _TOKENS_LAST_HOUR.set(0.0)
        except Exception:  # pragma: no cover
            pass

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _cleanup_locked(self, now: float) -> None:
        """Evict expired records while holding the lock."""
        hourly_cutoff = now - self._window_s
        while self._records and self._records[0].timestamp < hourly_cutoff:
            self._records.popleft()

        daily_cutoff = now - self._daily_window_s
        while self._daily_records and self._daily_records[0].timestamp < daily_cutoff:
            self._daily_records.popleft()

    def _check_alerts_locked(self) -> None:
        """Check alert thresholds while holding the lock (non-blocking)."""
        hourly_total = sum(r.total_tokens for r in self._records)
        daily_total = sum(r.total_tokens for r in self._daily_records)

        # Hourly threshold
        if self._hourly_threshold > 0 and hourly_total > self._hourly_threshold:
            if not self._hourly_alert_triggered:
                logger.warning(
                    "llm_token_alert level=hourly total=%d threshold=%d",
                    hourly_total,
                    self._hourly_threshold,
                )
            self._hourly_alert_triggered = True
            try:
                _ALERT_FIRED.labels(level="hourly").inc()
            except Exception:  # pragma: no cover
                logger.debug("Alert counter increment failed", exc_info=True)
        else:
            self._hourly_alert_triggered = False

        # Daily threshold
        if self._daily_threshold > 0 and daily_total > self._daily_threshold:
            if not self._daily_alert_triggered:
                logger.warning(
                    "llm_token_alert level=daily total=%d threshold=%d",
                    daily_total,
                    self._daily_threshold,
                )
            self._daily_alert_triggered = True
            try:
                _ALERT_FIRED.labels(level="daily").inc()
            except Exception:  # pragma: no cover
                logger.debug("Alert counter increment failed", exc_info=True)
        else:
            self._daily_alert_triggered = False


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _safe_int(value: Any, default: int = 0) -> int:
    """Defensively convert *value* to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Defensively convert *value* to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------- #
# Module-level singleton
# ---------------------------------------------------------------------- #
_tracker: Optional[TokenTracker] = None
_tracker_lock = threading.Lock()


def get_token_tracker() -> TokenTracker:
    """Return the module-level :class:`TokenTracker` singleton."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = TokenTracker()
    return _tracker


def reset_token_tracker() -> None:
    """Reset the module-level singleton (intended for testing only)."""
    global _tracker
    with _tracker_lock:
        _tracker = None


def record_token_usage(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float = 0.0,
    cached: bool = False,
) -> None:
    """Convenience function – record one LLM call's token usage.

    Args:
        model: Model identifier string.
        prompt_tokens: Number of input/prompt tokens.
        completion_tokens: Number of output/completion tokens.
        latency_ms: End-to-end call latency in milliseconds.
        cached: Whether the response was served from cache.
    """
    get_token_tracker().record(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cached=cached,
    )


__all__ = [
    "TokenUsageRecord",
    "TokenTracker",
    "get_token_tracker",
    "reset_token_tracker",
    "record_token_usage",
]
