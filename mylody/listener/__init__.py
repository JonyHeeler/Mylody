"""音乐监听模块：监听 Windows 当前播放的媒体信息"""

import asyncio
import logging
from typing import Callable, Optional

from mylody.config import Config
from mylody.listener.debounce import Debouncer
from mylody.listener.media_session import MediaSessionManager
from mylody.types import MediaInfo

logger = logging.getLogger("mylody.listener")


class MediaListener:
    """媒体监听器：组合 MediaSessionManager + Debouncer，实现完整的监听流程

    Args:
        config: 配置对象
        on_track_change: 曲目变化时的回调函数
    """

    def __init__(self, config: Config, on_track_change: Callable) -> None:
        self._config = config
        self._on_track_change = on_track_change
        self._media_session = MediaSessionManager()
        self._debouncer = Debouncer(
            delay_seconds=config.get("listener.debounce_seconds", 3),
            callback=self._handle_debounced_change,
        )
        self._current_track: Optional[MediaInfo] = None
        self._pending_track: Optional[MediaInfo] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def current_track(self) -> Optional[MediaInfo]:
        """获取当前播放的曲目信息

        Returns:
            Optional[MediaInfo]: 当前曲目信息
        """
        return self._current_track

    async def start(self) -> None:
        """启动媒体监听"""
        if self._running:
            logger.warning("媒体监听器已在运行中")
            return

        initialized = await self._media_session.initialize()
        if not initialized:
            logger.error("媒体会话管理器初始化失败，监听器无法启动")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("媒体监听器已启动")

    async def stop(self) -> None:
        """停止媒体监听"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._debouncer.cancel()
        logger.info("媒体监听器已停止")

    async def _poll_loop(self) -> None:
        """轮询循环：定期检查媒体信息"""
        poll_interval = self._config.get("listener.poll_interval_seconds", 2)

        while self._running:
            try:
                info = await self._media_session.get_current_info()

                if info is None:
                    if self._current_track is not None:
                        logger.debug("媒体播放已停止")
                        self._current_track = None
                    await asyncio.sleep(poll_interval)
                    continue

                excluded_apps = self._config.get("listener.excluded_apps", [])
                if self._media_session.is_excluded(info, excluded_apps):
                    await asyncio.sleep(poll_interval)
                    continue

                if self._is_same_track(info):
                    await asyncio.sleep(poll_interval)
                    continue
                if self._is_same_pending_track(info):
                    await asyncio.sleep(poll_interval)
                    continue

                logger.info("检测到新曲目: %s - %s", info.title, info.artist)
                self._pending_track = info
                await self._debouncer.trigger(info)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("轮询循环异常: %s", e)

            await asyncio.sleep(poll_interval)

    def _is_same_track(self, new_info: MediaInfo) -> bool:
        """检查是否与当前曲目相同

        Args:
            new_info: 新的媒体信息

        Returns:
            bool: 是否相同
        """
        if self._current_track is None:
            return False
        return (
            self._current_track.title == new_info.title
            and self._current_track.artist == new_info.artist
        )

    def _is_same_pending_track(self, new_info: MediaInfo) -> bool:
        """检查是否与等待防抖确认的曲目相同"""
        if self._pending_track is None or not self._debouncer.is_pending:
            return False
        return (
            self._pending_track.title == new_info.title
            and self._pending_track.artist == new_info.artist
        )

    async def _handle_debounced_change(self, info: MediaInfo) -> None:
        """处理防抖后的曲目变化

        Args:
            info: 新的媒体信息
        """
        self._current_track = info
        self._pending_track = None
        logger.info("曲目变化确认: %s - %s", info.title, info.artist)
        try:
            await self._on_track_change(info)
        except Exception as e:
            logger.error("曲目变化回调执行失败: %s", e)


__all__ = ["MediaSessionManager", "Debouncer", "MediaListener"]
