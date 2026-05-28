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

        session = self._manager.get_current_session()
        if not session:
            return None

        try:
            props = await session.try_get_media_properties_async()
            playback = session.get_playback_info()
            status_code = playback.playback_status

            return MediaInfo(
                title=props.title or "未知歌曲",
                artist=props.artist or "未知艺术家",
                album=props.album_title or "未知专辑",
                album_artist=props.album_artist or "",
                source_app=session.source_app_user_model_id or "",
                playback_status=status_code,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.debug("获取媒体信息失败: %s", e)
            return None
