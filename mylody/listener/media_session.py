"""WinRT 媒体会话封装：查询 Windows 当前播放的媒体信息"""

import logging
from datetime import datetime, timezone
from typing import Optional

from mylody.types import MediaInfo

logger = logging.getLogger("mylody.listener.media_session")
ARTIST_ALBUM_SEPARATORS = (" — ", " – ", " - ")

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
            timeline = self._get_timeline(session)

            title = props.title.strip() if props.title else ""
            artist = props.artist.strip() if props.artist else ""
            album = props.album_title.strip() if props.album_title else ""
            album_artist = props.album_artist.strip() if props.album_artist else ""
            artist, album = self._split_artist_album(artist, album)
            track_number = self._safe_int(getattr(props, "track_number", 0))
            album_track_count = self._safe_int(getattr(props, "album_track_count", 0))
            genres = self._safe_list(getattr(props, "genres", []))
            if status_code != 4 or not title:
                return None

            return MediaInfo(
                title=title,
                artist=artist or "未知艺术家",
                album=album or "未知专辑",
                album_artist=album_artist,
                track_number=track_number,
                album_track_count=album_track_count,
                genres=genres,
                duration_ms=self._timespan_to_ms(getattr(timeline, "end_time", None)),
                position_ms=self._timespan_to_ms(getattr(timeline, "position", None)),
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
            if status_code != 4:
                return None

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

    @staticmethod
    def _split_artist_album(artist: str, album: str) -> tuple[str, str]:
        """Apple Music sometimes puts 'artist — album' in artist fields."""
        if album and album != "未知专辑":
            return artist, album

        for separator in ARTIST_ALBUM_SEPARATORS:
            if separator in artist:
                left, right = artist.split(separator, 1)
                if left.strip() and right.strip():
                    return left.strip(), right.strip()

        return artist, album

    @staticmethod
    def _get_timeline(session):
        try:
            return session.get_timeline_properties()
        except Exception:
            return None

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_list(value) -> list[str]:
        try:
            return [str(item).strip() for item in value if str(item).strip()]
        except TypeError:
            return []

    @staticmethod
    def _timespan_to_ms(value) -> int:
        if value is None:
            return 0
        if hasattr(value, "total_seconds"):
            return int(value.total_seconds() * 1000)
        try:
            return int(value) // 10_000
        except (TypeError, ValueError):
            return 0
