"""Evidence 模块数据类型定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArtistInfo:
    """艺术家信息

    Attributes:
        mbid: MusicBrainz ID
        name: 艺术家名称
        sort_name: 排序名称
        disambiguation: 消歧义说明
    """
    mbid: str = ""
    name: str = ""
    sort_name: str = ""
    disambiguation: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mbid": self.mbid,
            "name": self.name,
            "sort_name": self.sort_name,
            "disambiguation": self.disambiguation,
        }


@dataclass
class GenreTag:
    """流派/标签

    Attributes:
        name: 名称
        count: 投票数量
    """
    name: str = ""
    count: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"name": self.name, "count": self.count}


@dataclass
class CoverArt:
    """封面图信息

    Attributes:
        image: 原始图片 URL
        thumbnail_250: 250px 缩略图
        thumbnail_500: 500px 缩略图
        thumbnail_1200: 1200px 缩略图
    """
    image: str = ""
    thumbnail_250: str = ""
    thumbnail_500: str = ""
    thumbnail_1200: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "image": self.image,
            "thumbnail_250": self.thumbnail_250,
            "thumbnail_500": self.thumbnail_500,
            "thumbnail_1200": self.thumbnail_1200,
        }


@dataclass
class ReleaseInfo:
    """发行版本信息

    Attributes:
        mbid: MusicBrainz ID
        title: 专辑名称
        date: 发行日期
        country: 国家
        status: 状态
        barcode: 条形码
        label_names: 厂牌列表
        cover_art: 封面图信息
    """
    mbid: str = ""
    title: str = ""
    date: str = ""
    country: str = ""
    status: str = ""
    barcode: str = ""
    label_names: list[str] = field(default_factory=list)
    cover_art: Optional[CoverArt] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mbid": self.mbid,
            "title": self.title,
            "date": self.date,
            "country": self.country,
            "status": self.status,
            "barcode": self.barcode,
            "label_names": self.label_names,
            "cover_art": self.cover_art.to_dict() if self.cover_art else None,
        }


@dataclass
class MusicMetadata:
    """音乐元数据（从 MusicBrainz 获取并清洗）

    Attributes:
        recording_mbid: Recording MusicBrainz ID
        title: 歌曲标题
        length_ms: 时长（毫秒）
        artists: 艺术家列表
        releases: 发行版本列表
        isrcs: ISRC 列表
        genres: 流派列表
        tags: 标签列表
        external_urls: 外部链接
        source: 数据来源
        fetched_at: 获取时间
    """
    recording_mbid: str = ""
    title: str = ""
    length_ms: int = 0
    artists: list[ArtistInfo] = field(default_factory=list)
    releases: list[ReleaseInfo] = field(default_factory=list)
    isrcs: list[str] = field(default_factory=list)
    genres: list[GenreTag] = field(default_factory=list)
    tags: list[GenreTag] = field(default_factory=list)
    external_urls: list[dict] = field(default_factory=list)
    source: str = "musicbrainz"
    fetched_at: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "recording_mbid": self.recording_mbid,
            "title": self.title,
            "length_ms": self.length_ms,
            "artists": [a.to_dict() for a in self.artists],
            "releases": [r.to_dict() for r in self.releases],
            "isrcs": self.isrcs,
            "genres": [g.to_dict() for g in self.genres],
            "tags": [t.to_dict() for t in self.tags],
            "external_urls": self.external_urls,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


@dataclass
class MusicSearchResult:
    """搜索结果

    Attributes:
        recording_mbid: Recording MusicBrainz ID
        title: 歌曲标题
        score: 匹配分数
        length_ms: 时长（毫秒）
        artist_credit: 艺术家署名
        first_release_date: 首次发行日期
        releases: 候选发行版本
    """
    recording_mbid: str = ""
    title: str = ""
    score: int = 0
    length_ms: int = 0
    artist_credit: str = ""
    first_release_date: str = ""
    releases: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "recording_mbid": self.recording_mbid,
            "title": self.title,
            "score": self.score,
            "length_ms": self.length_ms,
            "artist_credit": self.artist_credit,
            "first_release_date": self.first_release_date,
            "releases": self.releases,
        }


@dataclass
class EvidenceSource:
    """证据来源

    Attributes:
        provider: 提供者名称
        url: 来源 URL
        title: 来源标题
        retrieved_at: 获取时间
    """
    provider: str = ""
    url: str = ""
    title: str = ""
    retrieved_at: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "provider": self.provider,
            "url": self.url,
            "title": self.title,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class EvidenceFact:
    """证据事实

    Attributes:
        key: 事实键名
        value: 事实值
        source: 来源
        confidence: 置信度
    """
    key: str = ""
    value: str = ""
    source: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class EvidenceBundle:
    """证据包

    Attributes:
        track_title: 歌曲标题
        artist: 艺术家
        album: 专辑
        canonical_id: 规范 ID
        known_facts: 已确认事实
        uncertain_facts: 未确认事实
        sources: 来源列表
        confidence: 整体置信度
        evidence_version: 版本
    """
    track_title: str = ""
    artist: str = ""
    album: str = ""
    canonical_id: str = ""
    known_facts: list[EvidenceFact] = field(default_factory=list)
    uncertain_facts: list[EvidenceFact] = field(default_factory=list)
    sources: list[EvidenceSource] = field(default_factory=list)
    confidence: float = 0.0
    evidence_version: str = "evidence_v1"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "track_title": self.track_title,
            "artist": self.artist,
            "album": self.album,
            "canonical_id": self.canonical_id,
            "known_facts": [f.to_dict() for f in self.known_facts],
            "uncertain_facts": [f.to_dict() for f in self.uncertain_facts],
            "sources": [s.to_dict() for s in self.sources],
            "confidence": self.confidence,
            "evidence_version": self.evidence_version,
        }
