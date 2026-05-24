"""LLM 响应缓存模块.

提供基于内存的 LLM 调用缓存功能,通过 SHA-256 哈希键实现 LRU 淘汰策略,
避免重复请求相同 prompt,提升性能并降低 token 消耗.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from riskagent_agenticrag.config.settings import get_settings

logger = logging.getLogger(__name__)

__all__ = [
    "CachedResponse",
    "LLMCache",
    "get_llm_cache",
]


@dataclass
class CachedResponse:
    """LLM 缓存响应条目."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    cached_at: float  # time.time()


class LLMCache:
    """线程安全的 LRU 内存缓存,用于存储 LLM 响应.

    使用 OrderedDict 实现 LRU(最近最少使用)淘汰策略.
    仅缓存 temperature=0.0 的确定性请求.
    """

    def __init__(self, max_size: int = 1000) -> None:
        """初始化缓存.

        Args:
            max_size: 最大缓存条目数量,超过后淘汰最旧条目.
        """
        self._max_size = max_size
        self._store: OrderedDict[str, CachedResponse] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def make_key(
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """根据请求参数生成 SHA-256 缓存键.

        Args:
            messages: 消息列表.
            model: 模型名称.
            temperature: 采样温度.
            max_tokens: 最大生成 token 数,可为 None.

        Returns:
            64 位十六进制 SHA-256 哈希字符串.
        """
        key_data = {
            "messages": messages,
            "max_tokens": max_tokens,
            "model": model,
            "temperature": temperature,
        }
        key_json = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_json.encode()).hexdigest()

    def get(self, key: str) -> CachedResponse | None:
        """从缓存获取响应,命中时将条目移至末尾(LRU 更新).

        Args:
            key: 由 :meth:`make_key` 生成的缓存键.

        Returns:
            命中时返回 :class:`CachedResponse`,未命中返回 ``None``.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                self._store.move_to_end(key)
                logger.debug("Cache hit for key: %s...", key[:16])
                return entry
            logger.debug("Cache miss for key: %s...", key[:16])
            return None

    def put(self, key: str, response: CachedResponse) -> None:
        """将响应写入缓存.

        当缓存已满时,淘汰最旧(最久未访问)的条目.
        调用方负责确保仅在 temperature==0.0 时调用本方法.

        Args:
            key: 由 :meth:`make_key` 生成的缓存键.
            response: 需要缓存的 :class:`CachedResponse` 实例.
        """
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = response
                logger.debug("Cache updated for key: %s...", key[:16])
                return

            if len(self._store) >= self._max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug("Cache evicted oldest key: %s...", evicted_key[:16])

            self._store[key] = response
            logger.debug("Cache stored for key: %s...", key[:16])

    def clear(self) -> None:
        """清空所有缓存条目."""
        with self._lock:
            self._store.clear()
        logger.debug("Cache cleared")

    def size(self) -> int:
        """返回当前缓存条目数量."""
        with self._lock:
            return len(self._store)


# 模块级单例
_cache: LLMCache | None = None


def get_llm_cache() -> LLMCache:
    """获取全局 LLMCache 单例实例.

    首次调用时从 settings 读取 ``llm_governance.cache_max_size`` 初始化.

    Returns:
        全局共享的 :class:`LLMCache` 实例.
    """
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = LLMCache(max_size=settings.llm_governance.cache_max_size)
    return _cache
