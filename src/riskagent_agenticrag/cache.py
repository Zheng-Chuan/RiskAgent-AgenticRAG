"""RiskAgent 缓存模块 - 支持 Redis 缓存和内存缓存."""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Generic, TypeVar

from riskagent_agenticrag.config.settings import settings
from riskagent_agenticrag.exceptions import CacheConnectionError, CacheError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheBackend(ABC, Generic[T]):
    """缓存后端抽象基类."""

    @abstractmethod
    def get(self, key: str) -> T | None:
        """获取缓存值."""
        pass

    @abstractmethod
    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """设置缓存值."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存值."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查 key 是否存在."""
        pass


class InMemoryCache(CacheBackend[T]):
    """内存缓存后端."""

    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, tuple[T, float | None]] = {}
        self._max_size = max_size
        logger.debug("InMemoryCache initialized with max_size=%d", max_size)

    def get(self, key: str) -> T | None:
        import time
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if expiry is not None and time.time() > expiry:
            self.delete(key)
            return None
        return value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        import time
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        expiry = time.time() + ttl if ttl is not None else None
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def exists(self, key: str) -> bool:
        return key in self._cache

    def _evict_oldest(self) -> None:
        """淘汰最旧的缓存项."""
        if not self._cache:
            return
        oldest_key = next(iter(self._cache))
        self.delete(oldest_key)


class RedisCache(CacheBackend[T]):
    """Redis 缓存后端."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.redis.redis_url
        self._client = None
        self._connect()

    def _connect(self) -> None:
        """连接 Redis."""
        try:
            import redis
            self._client = redis.from_url(self._redis_url)
            self._client.ping()
            logger.info("RedisCache connected successfully")
        except ImportError:
            raise CacheError("redis package not installed")
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise CacheConnectionError(f"Failed to connect to Redis: {e}")

    def _serialize(self, value: Any) -> bytes:
        """序列化值."""
        try:
            return pickle.dumps(value)
        except Exception:
            return json.dumps(value, ensure_ascii=False).encode("utf-8")

    def _deserialize(self, data: bytes) -> Any:
        """反序列化值."""
        try:
            return pickle.loads(data)
        except Exception:
            try:
                return json.loads(data.decode("utf-8"))
            except Exception:
                return data

    def get(self, key: str) -> T | None:
        if self._client is None:
            return None
        try:
            data = self._client.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error("Redis get error: %s", e)
            return None

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        if self._client is None:
            return
        try:
            serialized = self._serialize(value)
            if ttl is not None:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
        except Exception as e:
            logger.error("Redis set error: %s", e)

    def delete(self, key: str) -> None:
        if self._client is None:
            return
        try:
            self._client.delete(key)
        except Exception as e:
            logger.error("Redis delete error: %s", e)

    def clear(self) -> None:
        if self._client is None:
            return
        try:
            self._client.flushdb()
        except Exception as e:
            logger.error("Redis clear error: %s", e)

    def exists(self, key: str) -> bool:
        if self._client is None:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error("Redis exists error: %s", e)
            return False


class CacheManager:
    """缓存管理器 - 管理多个缓存实例."""

    _instance: CacheManager | None = None
    _backends: dict[str, CacheBackend[Any]] = {}
    _default_backend: str = "default"

    def __new__(cls) -> CacheManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._setup_default_backends()

    def _setup_default_backends(self) -> None:
        """设置默认缓存后端."""
        try:
            self._backends["redis"] = RedisCache()
            self._default_backend = "redis"
            logger.info("Using Redis as default cache backend")
        except CacheError:
            self._backends["memory"] = InMemoryCache()
            self._default_backend = "memory"
            logger.info("Using InMemoryCache as default cache backend")

    def get_backend(self, name: str | None = None) -> CacheBackend[Any]:
        """获取缓存后端."""
        backend_name = name or self._default_backend
        if backend_name not in self._backends:
            raise CacheError(f"Cache backend '{backend_name}' not found")
        return self._backends[backend_name]

    def register_backend(self, name: str, backend: CacheBackend[Any]) -> None:
        """注册缓存后端."""
        self._backends[name] = backend


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """生成缓存 key."""
    key_parts = [
        func.__module__,
        func.__name__,
        str(args),
        str(sorted(kwargs.items())),
    ]
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()


def cached(
    ttl: int | None = 3600,
    backend: str | None = None,
    key_prefix: str = "",
) -> Callable:
    """缓存装饰器.

    Args:
        ttl: 缓存过期时间（秒），None 表示永不过期
        backend: 缓存后端名称
        key_prefix: key 前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = CacheManager()
            cache = cache_manager.get_backend(backend)
            cache_key = f"{key_prefix}:{_generate_cache_key(func, args, kwargs)}"

            result = cache.get(cache_key)
            if result is not None:
                logger.debug("Cache hit for key: %s", cache_key)
                return result

            logger.debug("Cache miss for key: %s", cache_key)
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


# 便捷函数
def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例."""
    return CacheManager()


def get_cache(backend: str | None = None) -> CacheBackend[Any]:
    """获取缓存后端."""
    return get_cache_manager().get_backend(backend)
