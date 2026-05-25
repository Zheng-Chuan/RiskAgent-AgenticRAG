"""性能基准测试 - 测试系统性能指标."""

from __future__ import annotations

import time
import uuid

import pytest

pytest.importorskip("pytest_benchmark")


class TestPerformanceBaseline:
    """性能基准测试."""

    @pytest.mark.benchmark
    def test_basic_function_performance(self, benchmark):
        """测试基础函数性能基准."""

        def simple_function(x: int) -> int:
            return x * x

        result = benchmark(simple_function, 42)
        assert result == 1764

    @pytest.mark.benchmark
    def test_string_operations(self, benchmark):
        """测试字符串操作性能."""

        def string_ops(n: int) -> str:
            return "test" * n

        result = benchmark(string_ops, 1000)
        assert len(result) == 4000

    @pytest.mark.benchmark
    def test_uuid_generation(self, benchmark):
        """测试 UUID 生成性能."""
        result = benchmark(uuid.uuid4)
        assert result is not None


class TestCachePerformance:
    """缓存性能测试."""

    def setup_method(self):
        """测试前设置."""
        from riskagent_agenticrag.cache import InMemoryCache
        self.cache = InMemoryCache()

    @pytest.mark.benchmark
    def test_cache_set_performance(self, benchmark):
        """测试缓存写入性能."""

        def cache_set():
            key = f"key_{uuid.uuid4()}"
            self.cache.set(key, "value", ttl=3600)

        benchmark(cache_set)

    @pytest.mark.benchmark
    def test_cache_get_performance(self, benchmark):
        """测试缓存读取性能."""
        self.cache.set("test_key", "test_value", ttl=3600)

        def cache_get():
            return self.cache.get("test_key")

        result = benchmark(cache_get)
        assert result == "test_value"


class TestTimingMeasurements:
    """时间测量测试."""

    def test_simple_timing(self):
        """简单的时间测量."""
        start = time.time()
        time.sleep(0.01)
        elapsed = time.time() - start
        assert elapsed >= 0.01

    def test_multiple_operations_timing(self):
        """测量多个操作的时间."""
        operations = 1000
        start = time.time()
        for i in range(operations):
            _ = i * i
        elapsed = time.time() - start
        ops_per_second = operations / elapsed if elapsed > 0 else 0
        assert ops_per_second > 0
