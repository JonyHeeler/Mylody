"""Evidence 业务层：整合搜索、详情查询、缓存、证据构建"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from mylody.evidence.client import MusicBrainzClient, NotFoundError
from mylody.evidence.external_service import ExternalEvidenceService
from mylody.evidence.external_types import (
    ArtistBackground,
    WikipediaMusicContext,
)
from mylody.evidence.mapper import (
    map_cover_art,
    map_recording_detail,
    map_recording_search_result,
    map_release,
)
from mylody.evidence.types import (
    EvidenceBundle,
    EvidenceFact,
    EvidenceSource,
    MusicMetadata,
    MusicSearchResult,
)

logger = logging.getLogger("mylody.evidence.service")

SEARCH_CACHE_TTL = timedelta(days=1)
RECORDING_CACHE_TTL = timedelta(days=7)


class EvidenceService:
    """Evidence 业务服务

    整合 MusicBrainz API 调用、缓存、证据构建。

    Attributes:
        _client: MusicBrainz 客户端
        _search_cache: 搜索结果缓存
        _recording_cache: Recording 详情缓存
    """

    def __init__(
        self,
        wikipedia_language: str = "en",
    ) -> None:
        self._client = MusicBrainzClient()
        self._external = ExternalEvidenceService(
            wikipedia_language=wikipedia_language,
        )
        self._search_cache: dict[str, tuple[list[MusicSearchResult], datetime]] = {}
        self._recording_cache: dict[str, tuple[MusicMetadata, datetime]] = {}

    async def search_recordings(
        self,
        title: str,
        artist: str = "",
        limit: int = 10,
    ) -> list[MusicSearchResult]:
        """搜索 Recording

        Args:
            title: 歌曲标题
            artist: 艺术家名称
            limit: 返回数量限制

        Returns:
            list[MusicSearchResult]: 搜索结果列表
        """
        if not title:
            return []

        cache_key = self._make_cache_key("search", title=title, artist=artist)
        cached = self._get_from_cache(self._search_cache, cache_key)
        if cached is not None:
            return cached

        query = f'recording:"{title}"'
        if artist:
            query += f' AND artist:"{artist}"'

        try:
            data = await self._client.get(
                "/recording/",
                params={"query": query, "limit": limit},
            )
        except Exception as e:
            logger.error("搜索 Recording 失败: %s", e)
            return []

        results = [
            map_recording_search_result(r)
            for r in data.get("recordings", [])
        ]

        self._set_to_cache(
            self._search_cache, cache_key, results, SEARCH_CACHE_TTL
        )

        return results

    async def get_recording_metadata(
        self, recording_mbid: str
    ) -> Optional[MusicMetadata]:
        """获取 Recording 详情

        Args:
            recording_mbid: Recording MusicBrainz ID

        Returns:
            Optional[MusicMetadata]: 音乐元数据，不存在返回 None
        """
        if not recording_mbid:
            return None

        cached = self._get_from_cache(self._recording_cache, recording_mbid)
        if cached is not None:
            return cached

        try:
            data = await self._client.get(
                f"/recording/{recording_mbid}",
                params={
                    "inc": "artist-credits+releases+release-groups+isrcs+genres+tags+ratings+url-rels"
                },
            )
        except NotFoundError:
            logger.warning("Recording 不存在: %s", recording_mbid)
            return None
        except Exception as e:
            logger.error("获取 Recording 详情失败: %s", e)
            return None

        metadata = map_recording_detail(data)

        for release in metadata.releases[:3]:
            if not release.mbid:
                continue
            try:
                release_data = await self._client.get(
                    f"/release/{release.mbid}",
                    params={"inc": "artist-credits+labels+release-groups+genres+tags"},
                )
                enriched_release = map_release(release_data)
                release.date = release.date or enriched_release.date
                release.country = release.country or enriched_release.country
                release.status = release.status or enriched_release.status
                release.barcode = release.barcode or enriched_release.barcode
                release.label_names = release.label_names or enriched_release.label_names
                cover_data = await self._client.get_cover_art(release.mbid)
                if cover_data:
                    release.cover_art = map_cover_art(cover_data)
            except Exception as e:
                logger.debug("获取 Release 增强信息失败: %s - %s", release.mbid, e)

        self._set_to_cache(
            self._recording_cache, recording_mbid, metadata, RECORDING_CACHE_TTL
        )

        return metadata

    async def search_wikipedia_artist(
        self, artist: str
    ) -> Optional[ArtistBackground]:
        """Search Wikipedia for artist background.

        Args:
            artist: Artist name.

        Returns:
            ArtistBackground if a likely page is found, otherwise None.
        """
        return await self._external.search_wikipedia_artist(artist)

    async def search_wikipedia_music_context(
        self, title: str, artist: str = "", album: str = ""
    ) -> Optional[WikipediaMusicContext]:
        """Search Wikipedia for song, release and artist context."""
        return await self._external.search_wikipedia_music_context(
            title, artist, album
        )

    def build_evidence(
        self,
        track_title: str,
        artist: str,
        album: str,
        metadata: Optional[MusicMetadata],
        search_score: int = 0,
    ) -> EvidenceBundle:
        """构建证据包

        Args:
            track_title: 歌曲标题
            artist: 艺术家
            album: 专辑
            metadata: MusicBrainz 元数据
            search_score: MusicBrainz 搜索匹配分数 (0-100)

        Returns:
            EvidenceBundle: 证据包
        """
        if metadata is None:
            return EvidenceBundle(
                track_title=track_title,
                artist=artist,
                album=album,
                confidence=0.0,
            )

        known_facts = []
        uncertain_facts = []
        sources = []

        source = EvidenceSource(
            provider="musicbrainz",
            url=f"https://musicbrainz.org/recording/{metadata.recording_mbid}",
            title=metadata.title,
            retrieved_at=metadata.fetched_at,
        )
        sources.append(source)

        artist_names = ", ".join(a.name for a in metadata.artists)
        if artist_names:
            known_facts.append(EvidenceFact(
                key="artists",
                value=artist_names,
                source="musicbrainz",
                confidence=0.95,
            ))

        if metadata.isrcs:
            known_facts.append(EvidenceFact(
                key="isrcs",
                value=", ".join(metadata.isrcs),
                source="musicbrainz",
                confidence=0.99,
            ))

        for genre in metadata.genres[:5]:
            known_facts.append(EvidenceFact(
                key="genre",
                value=genre.name,
                source="musicbrainz",
                confidence=0.8,
            ))

        for tag in metadata.tags[:10]:
            uncertain_facts.append(EvidenceFact(
                key="tag",
                value=tag.name,
                source="musicbrainz",
                confidence=0.6,
            ))

        for release in metadata.releases[:3]:
            release_info = release.title
            if release.date:
                release_info += f" ({release.date})"
            if release.label_names:
                release_info += f" [{', '.join(release.label_names)}]"

            fact = EvidenceFact(
                key="release",
                value=release_info,
                source="musicbrainz",
                confidence=0.85,
            )

            if release == metadata.releases[0]:
                known_facts.append(fact)
            else:
                uncertain_facts.append(fact)

        for url_info in metadata.external_urls[:5]:
            uncertain_facts.append(EvidenceFact(
                key=f"external_url:{url_info.get('type', 'unknown')}",
                value=url_info.get("url", ""),
                source="musicbrainz",
                confidence=0.7,
            ))

        confidence = self._calculate_confidence(
            track_title, artist, album, metadata, search_score, known_facts
        )

        return EvidenceBundle(
            track_title=track_title,
            artist=artist,
            album=album,
            canonical_id=metadata.recording_mbid,
            known_facts=known_facts,
            uncertain_facts=uncertain_facts,
            sources=sources,
            confidence=confidence,
        )

    @staticmethod
    def _calculate_confidence(
        track_title: str,
        artist: str,
        album: str,
        metadata: MusicMetadata,
        search_score: int,
        known_facts: list[EvidenceFact],
    ) -> float:
        """计算证据置信度

        基于以下因素：
        1. MusicBrainz 搜索匹配分数 (0-100)
        2. 标题/艺术家/专辑名称匹配度
        3. 已确认事实数量

        Args:
            track_title: 歌曲标题
            artist: 艺术家
            album: 专辑
            metadata: MusicBrainz 元数据
            search_score: 搜索匹配分数
            known_facts: 已确认事实列表

        Returns:
            float: 置信度 (0.0-1.0)
        """
        if not known_facts:
            return 0.0

        score_confidence = search_score / 100.0

        title_match = 0.0
        if track_title and metadata.title:
            title_lower = track_title.lower().strip()
            meta_title_lower = metadata.title.lower().strip()
            if title_lower == meta_title_lower:
                title_match = 1.0
            elif title_lower in meta_title_lower or meta_title_lower in title_lower:
                title_match = 0.7

        artist_match = 0.0
        if artist and metadata.artists:
            artist_lower = artist.lower().strip()
            meta_artists = [a.name.lower().strip() for a in metadata.artists]
            if artist_lower in meta_artists:
                artist_match = 1.0
            elif any(artist_lower in a or a in artist_lower for a in meta_artists):
                artist_match = 0.7

        confidence = (
            score_confidence * 0.4
            + title_match * 0.3
            + artist_match * 0.2
            + min(len(known_facts) / 5.0, 1.0) * 0.1
        )

        return min(confidence, 1.0)

    @staticmethod
    def _make_cache_key(prefix: str, **kwargs: str) -> str:
        """生成缓存键

        Args:
            prefix: 键前缀
            **kwargs: 键值对

        Returns:
            str: 缓存键
        """
        raw = json.dumps(kwargs, sort_keys=True)
        hash_str = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_str}"

    @staticmethod
    def _get_from_cache(
        cache: dict, key: str
    ) -> Optional[Union[list[MusicSearchResult], MusicMetadata]]:
        """从缓存获取

        Args:
            cache: 缓存字典
            key: 缓存键

        Returns:
            Optional: 缓存值，不存在或过期返回 None
        """
        if key not in cache:
            return None

        value, expires_at = cache[key]
        if datetime.now(timezone.utc) > expires_at:
            del cache[key]
            return None

        return value

    @staticmethod
    def _set_to_cache(
        cache: dict,
        key: str,
        value: Union[list[MusicSearchResult], MusicMetadata],
        ttl: timedelta,
    ) -> None:
        """写入缓存

        Args:
            cache: 缓存字典
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
        """
        expires_at = datetime.now(timezone.utc) + ttl
        cache[key] = (value, expires_at)

    async def close(self) -> None:
        """关闭服务"""
        await self._client.close()
        await self._external.close()
