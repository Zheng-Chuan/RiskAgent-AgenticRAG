"""Token tracker 单元测试 -- 覆盖 LLM token 用量追踪与告警逻辑."""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest

from riskagent_agenticrag.llm.token_tracker import (
    TokenTracker,
    TokenUsageRecord,
    _safe_float,
    _safe_int,
    get_token_tracker,
    record_token_usage,
    reset_token_tracker,
)


# ---------------------------------------------------------------------------
# 辅助函数 _safe_int / _safe_float
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafeInt:
    """_safe_int 防御性转换测试."""

    def test_none_returns_default(self):
        assert _safe_int(None) == 0

    def test_int_value(self):
        assert _safe_int(42) == 42

    def test_float_value_truncates(self):
        assert _safe_int(3.9) == 3

    def test_string_numeric(self):
        assert _safe_int("100") == 100

    def test_string_float_falls_back_to_float_conversion(self):
        assert _safe_int("3.7") == 3

    def test_invalid_string_returns_default(self):
        assert _safe_int("abc") == 0

    def test_invalid_type_returns_default(self):
        assert _safe_int({"x": 1}) == 0

    def test_custom_default(self):
        assert _safe_int(None, default=5) == 5


@pytest.mark.unit
class TestSafeFloat:
    """_safe_float 防御性转换测试."""

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_float_value(self):
        assert _safe_float(1.5) == 1.5

    def test_int_value(self):
        assert _safe_float(10) == 10.0

    def test_string_numeric(self):
        assert _safe_float("2.5") == 2.5

    def test_invalid_string_returns_default(self):
        assert _safe_float("abc") == 0.0

    def test_invalid_type_returns_default(self):
        assert _safe_float([1, 2]) == 0.0


# ---------------------------------------------------------------------------
# TokenTracker.record + get_usage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTokenTrackerRecord:
    """TokenTracker.record 记录 token 用量测试."""

    def test_record_single_call(self):
        tracker = TokenTracker()
        tracker.record(model="test-model", prompt_tokens=100, completion_tokens=50, latency_ms=200.0)
        usage = tracker.get_usage()
        assert usage["total_tokens"] == 150
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["calls"] == 1
        assert "by_model" in usage
        assert "test-model" in usage["by_model"]

    def test_record_cached_call(self):
        tracker = TokenTracker()
        tracker.record(model="m", prompt_tokens=10, completion_tokens=5, cached=True)
        usage = tracker.get_usage()
        assert usage["calls"] == 1

    def test_record_with_none_model_uses_unknown(self):
        tracker = TokenTracker()
        tracker.record(model=None, prompt_tokens=10, completion_tokens=5)
        usage = tracker.get_usage()
        assert "unknown" in usage["by_model"]

    def test_record_with_invalid_token_values_uses_safe_conversion(self):
        tracker = TokenTracker()
        tracker.record(model="m", prompt_tokens="50", completion_tokens="abc", latency_ms="100")
        usage = tracker.get_usage()
        # prompt_tokens=50, completion_tokens=0 (abc -> default)
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 0

    def test_record_multiple_models_aggregates_by_model(self):
        tracker = TokenTracker()
        tracker.record(model="a", prompt_tokens=10, completion_tokens=5)
        tracker.record(model="b", prompt_tokens=20, completion_tokens=10)
        usage = tracker.get_usage()
        assert usage["by_model"]["a"]["total_tokens"] == 15
        assert usage["by_model"]["b"]["total_tokens"] == 30
        assert usage["total_tokens"] == 45
        assert usage["calls"] == 2

    def test_record_with_zero_latency_skips_histogram(self):
        tracker = TokenTracker()
        # latency_ms=0 不应抛异常
        tracker.record(model="m", prompt_tokens=10, completion_tokens=5, latency_ms=0.0)
        usage = tracker.get_usage()
        assert usage["calls"] == 1


# ---------------------------------------------------------------------------
# 滑动窗口清理
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSlidingWindow:
    """滑动窗口过期清理测试."""

    def test_old_hourly_records_evicted(self):
        tracker = TokenTracker(window_s=1, daily_window_s=86400)
        tracker.record(model="m", prompt_tokens=100, completion_tokens=50)
        # 等待超过 hourly 窗口
        time.sleep(1.2)
        tracker.record(model="m", prompt_tokens=10, completion_tokens=5)
        usage = tracker.get_usage()
        # 第一条记录应已过期, 只剩第二条
        assert usage["total_tokens"] == 15

    def test_old_daily_records_evicted(self):
        tracker = TokenTracker(window_s=1, daily_window_s=1)
        tracker.record(model="m", prompt_tokens=100, completion_tokens=50)
        time.sleep(1.2)
        tracker.record(model="m", prompt_tokens=10, completion_tokens=5)
        usage = tracker.get_usage()
        assert usage["daily_total_tokens"] == 15


# ---------------------------------------------------------------------------
# 告警阈值
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAlertThresholds:
    """告警阈值触发测试."""

    def test_hourly_alert_triggers_when_exceeded(self):
        tracker = TokenTracker(window_s=3600, daily_window_s=86400)
        # 通过 mock settings 设置很低的阈值
        with patch.object(tracker, "_hourly_threshold", 50):
            tracker.record(model="m", prompt_tokens=30, completion_tokens=30)
            usage = tracker.get_usage()
            assert usage["hourly_alert_triggered"] is True

    def test_daily_alert_triggers_when_exceeded(self):
        tracker = TokenTracker(window_s=3600, daily_window_s=86400)
        with patch.object(tracker, "_daily_threshold", 20):
            tracker.record(model="m", prompt_tokens=15, completion_tokens=10)
            usage = tracker.get_usage()
            assert usage["daily_alert_triggered"] is True

    def test_alert_clears_when_tokens_drop_below_threshold(self):
        tracker = TokenTracker(window_s=3600, daily_window_s=86400)
        with patch.object(tracker, "_hourly_threshold", 50):
            tracker.record(model="m", prompt_tokens=30, completion_tokens=30)
            assert tracker.get_usage()["hourly_alert_triggered"] is True
            # 等待窗口过期
            time.sleep(0.1)
            tracker._window_s = 0
            tracker.record(model="m2", prompt_tokens=1, completion_tokens=0)
            # 旧记录过期后, 总量下降, 告警应清除
            usage = tracker.get_usage()
            assert usage["hourly_alert_triggered"] is False

    def test_zero_threshold_never_triggers_alert(self):
        tracker = TokenTracker(window_s=3600, daily_window_s=86400)
        with patch.object(tracker, "_hourly_threshold", 0):
            tracker.record(model="m", prompt_tokens=10000, completion_tokens=5000)
            usage = tracker.get_usage()
            assert usage["hourly_alert_triggered"] is False


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReset:
    """TokenTracker.reset 测试."""

    def test_reset_clears_records(self):
        tracker = TokenTracker()
        tracker.record(model="m", prompt_tokens=100, completion_tokens=50)
        tracker.reset()
        usage = tracker.get_usage()
        assert usage["total_tokens"] == 0
        assert usage["calls"] == 0

    def test_reset_clears_alert_flags(self):
        tracker = TokenTracker(window_s=3600, daily_window_s=86400)
        with patch.object(tracker, "_hourly_threshold", 10):
            tracker.record(model="m", prompt_tokens=20, completion_tokens=20)
            assert tracker.get_usage()["hourly_alert_triggered"] is True
        tracker.reset()
        assert tracker.get_usage()["hourly_alert_triggered"] is False


# ---------------------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModuleSingleton:
    """get_token_tracker / reset_token_tracker / record_token_usage 单例测试."""

    def test_get_token_tracker_returns_singleton(self):
        reset_token_tracker()
        t1 = get_token_tracker()
        t2 = get_token_tracker()
        assert t1 is t2

    def test_reset_token_tracker_creates_new_instance(self):
        reset_token_tracker()
        t1 = get_token_tracker()
        reset_token_tracker()
        t2 = get_token_tracker()
        assert t1 is not t2

    def test_record_token_usage_delegates_to_tracker(self):
        reset_token_tracker()
        record_token_usage(model="singleton-test", prompt_tokens=5, completion_tokens=3)
        tracker = get_token_tracker()
        usage = tracker.get_usage()
        assert usage["total_tokens"] == 8
        reset_token_tracker()


# ---------------------------------------------------------------------------
# TokenUsageRecord 数据类
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTokenUsageRecord:
    """TokenUsageRecord 数据类测试."""

    def test_default_values(self):
        rec = TokenUsageRecord(timestamp=1.0, model="m", prompt_tokens=10, completion_tokens=5, total_tokens=15)
        assert rec.latency_ms == 0.0
        assert rec.cached is False

    def test_explicit_values(self):
        rec = TokenUsageRecord(
            timestamp=1.0, model="m", prompt_tokens=10, completion_tokens=5, total_tokens=15,
            latency_ms=100.0, cached=True,
        )
        assert rec.latency_ms == 100.0
        assert rec.cached is True


# ---------------------------------------------------------------------------
# 边界条件
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEdgeCases:
    """边界条件测试."""

    def test_invalid_window_defaults_to_3600(self):
        tracker = TokenTracker(window_s=0, daily_window_s=0)
        assert tracker._window_s == 3600
        assert tracker._daily_window_s == 86400

    def test_negative_window_defaults(self):
        tracker = TokenTracker(window_s=-1, daily_window_s=-1)
        assert tracker._window_s == 3600

    def test_get_usage_window_hours(self):
        tracker = TokenTracker(window_s=7200)
        usage = tracker.get_usage()
        assert usage["window_hours"] == 2

    def test_get_usage_returns_thresholds(self):
        tracker = TokenTracker()
        usage = tracker.get_usage()
        assert "alert_threshold_hourly" in usage
        assert "alert_threshold_daily" in usage
