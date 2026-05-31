"""MusicBrainz 请求限流器：确保不超过 1 request/second"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger("mylody.evidence.rate_limiter")

T = TypeVar("T")

MIN_INTERVAL_MS = 1100


class RateLimiter:
    """异步限流器

    确保 MusicBrainz 请求不超过 1 request/second。
    使用全局单例模式，所有请求共享同一个限流队列。

    Attributes:
        _last_request_at: 上次请求时间戳
        _lock: 异步锁
    """

    _instance: "RateLimiter | None" = None

    def __new__(cls) -> "RateLimiter":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._last_request_at = 0.0
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def run(self, task: Callable[[], Awaitable[T]]) -> T:
        """执行限流任务

        Args:
            task: 异步任务函数

        Returns:
            T: 任务返回值
        """
        async with self._lock:
            now = time.time() * 1000
            elapsed = now - self._last_request_at
            wait_ms = max(0, MIN_INTERVAL_MS - elapsed)

            if wait_ms > 0:
                logger.debug("限流等待 %.0fms", wait_ms)
                await asyncio.sleep(wait_ms / 1000)

            self._last_request_at = time.time() * 1000
            return await task()

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）"""
        cls._instance = None
