"""WinRT 媒体会话封装：查询 Windows 当前播放的媒体信息"""

import logging
from datetime import datetime, timezone
from typing import Optional

from mylody.types import MediaInfo

logger = logging.getLogger("mylody.listener.media_session")

PLAYBACK_STATUS_MAP = {
    1: "stopped",
    2: "stopped",
    4: "playing",
    5: "paused",
}


class MediaSessionManager:
    """封装 Windows GlobalSystemMediaTransportControlsSessionManager

    提供异步接口查询当前播放的媒体信息，兼容 Spotify、网易云、Apple Music 等。
    """

    def __init__(self) -> None:
        self._manager = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化 WinRT 媒体会话管理器

        Returns:
            bool: 初始化是否成功
        """
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as MediaManager,
            )
            self._manager = await MediaManager.request_async()
            self._initialized = True
            logger.info("WinRT 媒体会话管理器初始化成功")
            return True
        except ImportError as e:
            logger.error("WinRT 模块未安装，请安装 winsdk: %s", e)
            self._initialized = False
            return False
        except Exception as e:
            logger.error("WinRT 媒体会话管理器初始化失败: %s", e)
            self._initialized = False
            return False

    async def get_current_info(self) -> Optional[MediaInfo]:
        """获取当前播放的媒体信息

        Returns:
            Optional[MediaInfo]: 媒体信息，无播放时返回 None
        """
        if not self._initialized or not self._manager:
            return None

        try:
            session = self._manager.get_current_session()
        except Exception as e:
            logger.error("获取媒体会话失败: %s", e)
            return None

        if not session:
            return None

        try:
            props = await session.try_get_media_properties_async()
            playback = session.get_playback_info()
            status_code = playback.playback_status

            title = props.title if props.title else "未知歌曲"
            artist = props.artist if props.artist else "未知艺术家"

            return MediaInfo(
                title=title,
                artist=artist,
                album=props.album_title or "未知专辑",
                album_artist=props.album_artist or "",
                source_app=session.source_app_user_model_id or "",
                playback_status=status_code,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.debug("获取媒体属性失败: %s", e)
            return self._try_window_title_fallback(session)

    def is_excluded(self, media_info: MediaInfo, excluded_apps: list[str]) -> bool:
        """检查当前来源应用是否在排除列表中

        Args:
            media_info: 媒体信息
            excluded_apps: 排除的应用列表

        Returns:
            bool: 是否应被排除
        """
        if not media_info.source_app:
            return False
        source_lower = media_info.source_app.lower()
        return any(app.lower() in source_lower for app in excluded_apps)

    def _try_window_title_fallback(self, session) -> Optional[MediaInfo]:
        """尝试通过窗口标题获取媒体信息（备用方案）

        Args:
            session: WinRT 媒体会话对象

        Returns:
            Optional[MediaInfo]: 媒体信息，失败时返回 None
        """
        try:
            playback = session.get_playback_info()
            status_code = playback.playback_status

            return MediaInfo(
                title="未知歌曲",
                artist="未知艺术家",
                album="未知专辑",
                album_artist="",
                source_app=session.source_app_user_model_id or "",
                playback_status=status_code,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.debug("窗口标题备用方案失败: %s", e)
            return None
