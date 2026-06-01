"""Helpers for converting evidence objects into AI prompt payloads."""

from typing import Optional

from mylody.evidence.external_types import (
    ArtistBackground,
    WikipediaMusicContext,
    WikipediaPage,
)
from mylody.evidence.types import EvidenceBundle


def format_ai_evidence(
    bundle: EvidenceBundle,
    artist_background: Optional[ArtistBackground] = None,
    wikipedia_context: Optional[WikipediaMusicContext] = None,
) -> dict:
    """Convert gathered evidence into the payload consumed by AI prompts.

    Args:
        bundle: MusicBrainz evidence bundle.
        artist_background: Optional Wikipedia artist summary.
        wikipedia_context: Optional precise Wikipedia music context.

    Returns:
        Dict payload containing known facts, uncertain facts, confidence and sources.
    """
    known_facts = [format_fact(fact.source, fact.key, fact.value) for fact in bundle.known_facts]
    uncertain_facts = [
        format_fact(fact.source, fact.key, fact.value)
        for fact in bundle.uncertain_facts
    ]
    sources = [source.to_dict() for source in bundle.sources]

    if artist_background is not None and artist_background.extract:
        known_facts.append(
            format_fact(
                "wikipedia",
                "artist_background",
                f"{artist_background.title}: {artist_background.extract}",
            )
        )
        sources.append({
            "provider": "wikipedia",
            "url": artist_background.url,
            "title": artist_background.title,
            "retrieved_at": artist_background.fetched_at,
        })

    if wikipedia_context is not None:
        for page in _iter_wikipedia_pages(wikipedia_context):
            known_facts.append(
                format_fact(
                    "wikipedia",
                    page.kind or "music_context",
                    f"{page.title}: {page.extract}",
                )
            )
            sources.append({
                "provider": "wikipedia",
                "url": page.url,
                "title": page.title,
                "retrieved_at": page.fetched_at,
            })

    return {
        "known_facts": known_facts,
        "uncertain_facts": uncertain_facts,
        "artist_background": (
            artist_background.to_dict() if artist_background is not None else None
        ),
        "wikipedia_context": (
            wikipedia_context.to_dict() if wikipedia_context is not None else None
        ),
        "confidence": bundle.confidence,
        "sources": sources,
    }


def format_fact(source: str, key: str, value: str) -> str:
    """Format a sourced fact for inclusion in an AI prompt."""
    return f"[{source}] {key}: {value}"


def _iter_wikipedia_pages(context: WikipediaMusicContext) -> list[WikipediaPage]:
    """Return available Wikipedia pages in usefulness order."""
    return [
        page
        for page in [context.song_page, context.release_page, context.artist_page]
        if page is not None and page.extract
    ]
