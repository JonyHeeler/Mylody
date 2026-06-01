"""External evidence data structures."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ArtistBackground:
    """Artist background sourced from Wikipedia."""

    artist: str = ""
    title: str = ""
    extract: str = ""
    description: str = ""
    url: str = ""
    source: str = "wikipedia"
    fetched_at: str = ""

    def to_dict(self) -> dict:
        """Convert artist background to a JSON-serializable dict."""
        return {
            "artist": self.artist,
            "title": self.title,
            "extract": self.extract,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


@dataclass
class WikipediaPage:
    """A Wikipedia page summary matched to a music entity."""

    kind: str = ""
    query: str = ""
    title: str = ""
    extract: str = ""
    description: str = ""
    url: str = ""
    matched_by: str = ""
    source: str = "wikipedia"
    fetched_at: str = ""

    def to_dict(self) -> dict:
        """Convert Wikipedia page data to a JSON-serializable dict."""
        return {
            "kind": self.kind,
            "query": self.query,
            "title": self.title,
            "extract": self.extract,
            "description": self.description,
            "url": self.url,
            "matched_by": self.matched_by,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


@dataclass
class WikipediaMusicContext:
    """Wikipedia context for song, release and artist entities."""

    song_page: Optional[WikipediaPage] = None
    release_page: Optional[WikipediaPage] = None
    artist_page: Optional[WikipediaPage] = None

    def to_dict(self) -> dict:
        """Convert Wikipedia music context to a JSON-serializable dict."""
        return {
            "song_page": self.song_page.to_dict() if self.song_page else None,
            "release_page": (
                self.release_page.to_dict() if self.release_page else None
            ),
            "artist_page": self.artist_page.to_dict() if self.artist_page else None,
        }
