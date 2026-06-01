"""External metadata clients for Wikipedia."""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx

from mylody.evidence.client import HEADERS
from mylody.evidence.external_types import (
    ArtistBackground,
    WikipediaMusicContext,
    WikipediaPage,
)


class WikipediaClient:
    """Small Wikipedia client using public REST/search endpoints."""

    def __init__(self, language: str = "en") -> None:
        self._language = language or "en"
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=20.0)

    async def search_artist(self, artist: str) -> Optional[ArtistBackground]:
        """Search a likely Wikipedia page for an artist.

        Args:
            artist: Artist name.

        Returns:
            Artist background summary when found.
        """
        if not artist:
            return None

        exact = await self._get_summary(artist)
        if exact is not None:
            return self._page_to_artist_background(artist, exact)

        search_url = f"https://{self._language}.wikipedia.org/w/api.php"
        response = await self._client.get(
            search_url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": f"{artist} musician",
                "format": "json",
                "srlimit": 1,
            },
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0].get("title", "")
        if not title:
            return None

        background = await self._get_summary(title)
        if background is not None:
            return self._page_to_artist_background(artist, background)
        return None

    async def search_music_context(
        self, title: str, artist: str = "", album: str = ""
    ) -> WikipediaMusicContext:
        """Search Wikipedia pages for song, release and artist context.

        Args:
            title: Song title.
            artist: Artist name.
            album: Album or release title.

        Returns:
            Wikipedia context split by music entity type.
        """
        song_page = None
        if title:
            song_page = await self._search_page(
                f'{title} {artist} song'.strip(),
                kind="song_background",
                required_text=artist,
            )

        release_page = None
        if album and album.lower().strip() != title.lower().strip():
            release_page = await self._search_page(
                f'{album} {artist} album'.strip(),
                kind="release_background",
                required_text=artist,
            )

        artist_page = None
        if artist:
            exact = await self._get_summary(artist)
            if exact is not None:
                artist_page = exact
                artist_page.kind = "artist_background"
                artist_page.query = artist
                artist_page.matched_by = "exact_title"
            if artist_page is None:
                artist_page = await self._search_page(
                    f"{artist} musician",
                    kind="artist_background",
                )

        return WikipediaMusicContext(
            song_page=song_page,
            release_page=release_page,
            artist_page=artist_page,
        )

    async def _search_page(
        self, query: str, kind: str, required_text: str = ""
    ) -> Optional[WikipediaPage]:
        """Search Wikipedia and return a summary for the best page."""
        search_url = f"https://{self._language}.wikipedia.org/w/api.php"
        response = await self._client.get(
            search_url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 1,
            },
        )
        response.raise_for_status()
        results = response.json().get("query", {}).get("search", [])
        if not results:
            return None

        page = await self._get_summary(results[0].get("title", ""))
        if page is None:
            return None
        if required_text and not self._page_contains(page, required_text):
            return None

        page.kind = kind
        page.query = query
        page.matched_by = "search"
        return page

    @staticmethod
    def _page_contains(page: WikipediaPage, text: str) -> bool:
        """Return whether a page title or extract contains the required text."""
        needle = text.lower().strip()
        haystack = f"{page.title} {page.description} {page.extract}".lower()
        return needle in haystack

    async def _get_summary(self, title: str) -> Optional[WikipediaPage]:
        """Fetch a Wikipedia page summary by exact title."""
        summary_url = (
            f"https://{self._language}.wikipedia.org/api/rest_v1/page/summary/"
            f"{quote(title, safe='')}"
        )
        summary_response = await self._client.get(summary_url)
        if summary_response.status_code == 404:
            return None
        summary_response.raise_for_status()
        data = summary_response.json()
        if data.get("type") == "disambiguation":
            return None

        return WikipediaPage(
            title=data.get("title", title),
            extract=data.get("extract", ""),
            description=data.get("description", ""),
            url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            matched_by="exact_title",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _page_to_artist_background(
        artist: str, page: WikipediaPage
    ) -> ArtistBackground:
        """Convert a generic Wikipedia page to the legacy artist background type."""
        return ArtistBackground(
            artist=artist,
            title=page.title,
            extract=page.extract,
            description=page.description,
            url=page.url,
            fetched_at=page.fetched_at,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
