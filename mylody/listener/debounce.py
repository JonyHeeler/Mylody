"""防抖模块：在连续事件稳定 N 秒后才触发回调"""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("mylody.listener.debounce")


class Debouncer:
    """防抖器：延迟触发回调，连续调用时重置计时

    适用于用户快速切歌场景，避免频繁触发 AI 请求。

    Args:
        delay_seconds: 延迟秒数
        callback: 触发时执行的异步回调函数
    """

    def __init__(self, delay_seconds: float, callback: Callable) -> None:
        self._delay = delay_seconds
        self._callback = callback
        self._task: Optional[asyncio.Task] = None
        self._last_data: Any = None

    async def trigger(self, data: Any) -> None:
        """触发防抖：取消上一次计时，重新开始倒计时

        Args:
            data: 传递给回调的数据
        """
        self.cancel()
        self._last_data = data
        self._task = asyncio.create_task(self._wait_and_fire(data))

    def cancel(self) -> None:
        """取消当前等待中的防抖任务"""
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def _wait_and_fire(self, data: Any) -> None:
        """等待延迟后执行回调

        Args:
            data: 传递给回调的数据
        """
        try:
            await asyncio.sleep(self._delay)
            logger.debug("防抖触发，执行回调")
            await self._callback(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("防抖回调执行失败: %s", e)

    @property
    def is_pending(self) -> bool:
        """是否有等待中的防抖任务

        Returns:
            bool: 是否有任务在等待
        """
        return self._task is not None and not self._task.done()
