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
        track_number: 曲目序号
        album_track_count: 专辑曲目总数
        genres: 流派标签
        duration_ms: 曲目时长（毫秒）
        position_ms: 当前播放位置（毫秒）
        source_app: 来源应用标识
        playback_status: 播放状态（4=播放中, 5=已暂停, 1=已停止）
        timestamp: 信息获取时间（ISO 8601）
    """
    title: str = "未知歌曲"
    artist: str = "未知艺术家"
    album: str = "未知专辑"
    album_artist: str = ""
    track_number: int = 0
    album_track_count: int = 0
    genres: list[str] = field(default_factory=list)
    duration_ms: int = 0
    position_ms: int = 0
    source_app: str = ""
    playback_status: int = 0
    timestamp: str = ""

    def is_playable_track(self) -> bool:
        """判断媒体信息是否足够代表一首正在播放的歌曲"""
        unknown_titles = {"", "未知歌曲", "unknown title", "unknown song"}

        title = (self.title or "").strip().lower()

        if title in unknown_titles:
            return False

        # Some tests, mocks, and fallback sources do not expose a WinRT playback
        # status. Treat status 0 as unknown instead of stopped so valid metadata
        # still flows through, while explicit paused/stopped states remain blocked.
        return self.playback_status in (0, 4)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "album_artist": self.album_artist,
            "track_number": self.track_number,
            "album_track_count": self.album_track_count,
            "genres": self.genres,
            "duration_ms": self.duration_ms,
            "position_ms": self.position_ms,
            "source_app": self.source_app,
            "playback_status": self.playback_status,
            "timestamp": self.timestamp,
        }


@dataclass
class ReviewData:
    """AI 乐评数据结构 v2

    Attributes:
        quote: 一句有记忆点的金句
        content: 一整段流畅的乐评文章
        emotion: 核心情绪关键词，如迷恋、怀旧、孤独、成长等
        similar_songs: 相似歌曲列表（3首）
        rating: 评分（0-10）
        factuality_level: 事实性等级 (metadata_only/grounded/mixed)
        analysis_basis: 分析依据来源 (track_metadata/provided_context/external_evidence)
        known_facts: 证据明确支持的事实列表
        uncertain_facts: 有可能相关但证据不足的信息列表
        safety_notes: 被降级、删除、限制的风险点列表
        evidence_sources: 来源 URL、平台、字段、置信度列表
        schema_version: 数据结构版本，用于缓存隔离
    """
    quote: str = ""
    content: str = ""
    emotion: str = ""
    similar_songs: list[str] = field(default_factory=list)
    rating: float = 0.0
    factuality_level: str = "metadata_only"
    analysis_basis: str = "track_metadata"
    known_facts: list[str] = field(default_factory=list)
    uncertain_facts: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    evidence_sources: list[dict] = field(default_factory=list)
    schema_version: str = "review_v2"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "quote": self.quote,
            "content": self.content,
            "emotion": self.emotion,
            "similar_songs": self.similar_songs,
            "rating": self.rating,
            "factuality_level": self.factuality_level,
            "analysis_basis": self.analysis_basis,
            "known_facts": self.known_facts,
            "uncertain_facts": self.uncertain_facts,
            "safety_notes": self.safety_notes,
            "evidence_sources": self.evidence_sources,
            "schema_version": self.schema_version,
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
