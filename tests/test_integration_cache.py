"""缓存集成测试 - 测试缓存功能."""

from __future__ import annotations

import time

import pytest

from riskagent_agenticrag.cache import CacheManager, InMemoryCache, RedisCache, cached, get_cache


class TestInMemoryCache:
    """内存缓存测试."""

    def test_set_and_get(self):
        """测试设置和获取值."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """测试获取不存在的键."""
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        """测试删除键."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        """测试清空缓存."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_exists(self):
        """测试键是否存在."""
        cache = InMemoryCache()
        assert not cache.exists("key1")
        cache.set("key1", "value1")
        assert cache.exists("key1")

    def test_ttl(self):
        """测试过期时间."""
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """测试 LRU 淘汰策略."""
        cache = InMemoryCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"


class TestCachedDecorator:
    """缓存装饰器测试."""

    def test_cached_decorator(self):
        """测试缓存装饰器."""
        call_count = 0

        @cached(ttl=3600)
        def add(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x + y

        assert add(2, 3) == 5
        assert call_count == 1
        assert add(2, 3) == 5
        assert call_count == 1
        assert add(3, 4) == 7
        assert call_count == 2


class TestCacheManager:
    """缓存管理器测试."""

    def test_get_cache(self):
        """测试获取缓存."""
        cache = get_cache()
        assert cache is not None

    def test_cache_manager_singleton(self):
        """测试缓存管理器单例."""
        manager1 = CacheManager()
        manager2 = CacheManager()
        assert manager1 is manager2


def test_cache_backend_operations():
    """测试缓存后端通用操作."""
    cache = InMemoryCache()
    test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    cache.set("complex", test_data)
    retrieved = cache.get("complex")
    assert retrieved == test_data
