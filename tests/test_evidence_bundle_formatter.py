"""Evidence formatter tests."""

from mylody.evidence.bundle_formatter import format_ai_evidence
from mylody.evidence.external_types import ArtistBackground
from mylody.evidence.types import EvidenceBundle, EvidenceFact


def test_format_ai_evidence_includes_wikipedia_context():
    """测试 Wikipedia 信息会进入 AI facts"""
    bundle = EvidenceBundle(
        confidence=0.8,
        known_facts=[
            EvidenceFact(
                key="artists",
                value="Radiohead",
                source="musicbrainz",
                confidence=0.95,
            )
        ],
    )
    background = ArtistBackground(
        artist="Radiohead",
        title="Radiohead",
        extract="Radiohead are an English rock band.",
        url="https://en.wikipedia.org/wiki/Radiohead",
    )

    payload = format_ai_evidence(bundle, background)

    assert any("artist_background" in fact for fact in payload["known_facts"])
    assert payload["artist_background"]["title"] == "Radiohead"
