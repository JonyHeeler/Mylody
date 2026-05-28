"""Mylody 数据结构定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MediaInfo:
    """当前播放的媒体信息

    Attributes:
        title: 歌曲名称
        artist: 艺术家
        album: 专辑名称
        album_artist: 专辑艺术家
        source_app: 来源应用标识
        playback_status: 播放状态（4=播放中, 5=已暂停, 1=已停止）
        timestamp: 信息获取时间（ISO 8601）
    """
    title: str = "未知歌曲"
    artist: str = "未知艺术家"
    album: str = "未知专辑"
    album_artist: str = ""
    source_app: str = ""
    playback_status: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "album_artist": self.album_artist,
            "source_app": self.source_app,
            "playback_status": self.playback_status,
            "timestamp": self.timestamp,
        }


@dataclass
class ReviewData:
    """AI 乐评数据结构

    Attributes:
        summary: 一句话概括（30字以内）
        emotion: 情感基调
        background: 创作背景或艺术家简介
        musicology: 音乐理论简析
        why_listen: 推荐理由
        similar_songs: 相似歌曲列表
        rating: 评分（0-10）
    """
    summary: str = ""
    emotion: str = ""
    background: str = ""
    musicology: str = ""
    why_listen: str = ""
    similar_songs: list[str] = field(default_factory=list)
    rating: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "summary": self.summary,
            "emotion": self.emotion,
            "background": self.background,
            "musicology": self.musicology,
            "why_listen": self.why_listen,
            "similar_songs": self.similar_songs,
            "rating": self.rating,
        }


@dataclass
class ServerStatus:
    """服务状态响应

    Attributes:
        running: 服务是否运行中
        current_track: 当前播放曲目信息
        uptime_seconds: 服务运行时长（秒）
    """
    running: bool = True
    current_track: Optional[MediaInfo] = None
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "running": self.running,
            "current_track": self.current_track.to_dict() if self.current_track else None,
            "uptime_seconds": round(self.uptime_seconds, 1),
        }
