"""External evidence service for Wikipedia metadata."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, TypeVar, Union

from mylody.evidence.external_clients import WikipediaClient
from mylody.evidence.external_types import (
    ArtistBackground,
    WikipediaMusicContext,
)

logger = logging.getLogger("mylody.evidence.external_service")

T = TypeVar("T", ArtistBackground, WikipediaMusicContext)
EXTERNAL_CACHE_TTL = timedelta(days=7)


class ExternalEvidenceService:
    """Coordinate external evidence providers and short-lived memory cache."""

    def __init__(
        self,
        wikipedia_language: str = "en",
    ) -> None:
        self._wikipedia = WikipediaClient(language=wikipedia_language)
        self._artist_cache: dict[
            str, tuple[Union[ArtistBackground, WikipediaMusicContext], datetime]
        ] = {}

    async def search_wikipedia_artist(
        self, artist: str
    ) -> Optional[ArtistBackground]:
        """Search Wikipedia for artist background.

        Args:
            artist: Artist name.

        Returns:
            Artist background when a likely page is found.
        """
        if not artist:
            return None

        cache_key = self._make_cache_key("artist_wiki", artist=artist)
        cached = self._get_from_cache(self._artist_cache, cache_key)
        if cached is not None:
            return cached

        try:
            background = await self._wikipedia.search_artist(artist)
        except Exception as e:
            logger.warning("Wikipedia 艺术家资料获取失败: %s", e)
            return None

        if background is not None:
            self._set_to_cache(
                self._artist_cache, cache_key, background, EXTERNAL_CACHE_TTL
            )
        return background

    async def search_wikipedia_music_context(
        self, title: str, artist: str = "", album: str = ""
    ) -> Optional[WikipediaMusicContext]:
        """Search Wikipedia for song, release and artist context.

        Args:
            title: Song title.
            artist: Artist name.
            album: Album or release title.

        Returns:
            Wikipedia context when any page is found.
        """
        cache_key = self._make_cache_key(
            "wiki_music", title=title, artist=artist, album=album
        )
        cached = self._get_from_cache(self._artist_cache, cache_key)
        if cached is not None:
            return cached

        try:
            context = await self._wikipedia.search_music_context(title, artist, album)
        except Exception as e:
            logger.warning("Wikipedia 音乐上下文获取失败: %s", e)
            return None

        if not any([context.song_page, context.release_page, context.artist_page]):
            return None

        self._set_to_cache(
            self._artist_cache, cache_key, context, EXTERNAL_CACHE_TTL
        )
        return context

    async def close(self) -> None:
        """Close external HTTP clients."""
        await self._wikipedia.close()

    @staticmethod
    def _make_cache_key(prefix: str, **kwargs: str) -> str:
        raw = json.dumps(kwargs, sort_keys=True)
        hash_str = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_str}"

    @staticmethod
    def _get_from_cache(cache: dict[str, tuple[T, datetime]], key: str) -> Optional[T]:
        if key not in cache:
            return None

        value, expires_at = cache[key]
        if datetime.now(timezone.utc) > expires_at:
            del cache[key]
            return None

        return value

    @staticmethod
    def _set_to_cache(
        cache: dict[str, tuple[T, datetime]],
        key: str,
        value: T,
        ttl: timedelta,
    ) -> None:
        expires_at = datetime.now(timezone.utc) + ttl
        cache[key] = (value, expires_at)
