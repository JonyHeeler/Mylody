"""Evidence Service 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mylody.evidence.service import EvidenceService
from mylody.evidence.types import (
    ArtistInfo,
    GenreTag,
    MusicMetadata,
    MusicSearchResult,
    ReleaseInfo,
)
from mylody.evidence.external_types import ArtistBackground


@pytest.fixture
def mock_service():
    """创建 mock 的 EvidenceService"""
    service = EvidenceService()
    service._client = AsyncMock()
    return service


@pytest.fixture
def sample_metadata():
    """创建示例 MusicMetadata"""
    return MusicMetadata(
        recording_mbid="test-mbid-123",
        title="Nude",
        length_ms=260000,
        artists=[ArtistInfo(mbid="artist-mbid", name="Radiohead")],
        releases=[
            ReleaseInfo(
                mbid="release-mbid",
                title="In Rainbows",
                date="2007-10-10",
                country="GB",
                label_names=["XL Recordings"],
            )
        ],
        isrcs=["GBAHT0600101"],
        genres=[GenreTag(name="alternative rock", count=50)],
        tags=[GenreTag(name="art rock", count=30)],
    )


def test_build_evidence_with_metadata(sample_metadata):
    """测试构建证据包（有元数据）"""
    service = EvidenceService()

    bundle = service.build_evidence(
        "Nude", "Radiohead", "In Rainbows", sample_metadata
    )

    assert bundle.track_title == "Nude"
    assert bundle.artist == "Radiohead"
    assert bundle.album == "In Rainbows"
    assert bundle.canonical_id == "test-mbid-123"
    assert bundle.confidence > 0

    fact_keys = [f.key for f in bundle.known_facts]
    assert "artists" in fact_keys
    assert "isrcs" in fact_keys
    assert "genre" in fact_keys
    assert "release" in fact_keys


def test_build_evidence_without_metadata():
    """测试构建证据包（无元数据）"""
    service = EvidenceService()

    bundle = service.build_evidence("Test", "Test", "Test", None)

    assert bundle.track_title == "Test"
    assert bundle.artist == "Test"
    assert bundle.confidence == 0.0
    assert len(bundle.known_facts) == 0
    assert len(bundle.sources) == 0


def test_build_evidence_artists(sample_metadata):
    """测试证据包中的艺术家信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    artists_facts = [f for f in bundle.known_facts if f.key == "artists"]
    assert len(artists_facts) == 1
    assert "Radiohead" in artists_facts[0].value


def test_build_evidence_isrcs(sample_metadata):
    """测试证据包中的 ISRC 信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    isrc_facts = [f for f in bundle.known_facts if f.key == "isrcs"]
    assert len(isrc_facts) == 1
    assert "GBAHT0600101" in isrc_facts[0].value


def test_build_evidence_genres(sample_metadata):
    """测试证据包中的流派信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    genre_facts = [f for f in bundle.known_facts if f.key == "genre"]
    assert len(genre_facts) == 1
    assert genre_facts[0].value == "alternative rock"


def test_build_evidence_tags(sample_metadata):
    """测试证据包中的标签信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    tag_facts = [f for f in bundle.uncertain_facts if f.key == "tag"]
    assert len(tag_facts) == 1
    assert tag_facts[0].value == "art rock"


def test_build_evidence_releases(sample_metadata):
    """测试证据包中的发行版本信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    release_facts = [f for f in bundle.known_facts if f.key == "release"]
    assert len(release_facts) == 1
    assert "In Rainbows" in release_facts[0].value
    assert "2007-10-10" in release_facts[0].value


def test_build_evidence_sources(sample_metadata):
    """测试证据包中的来源信息"""
    service = EvidenceService()

    bundle = service.build_evidence("Nude", "Radiohead", "", sample_metadata)

    assert len(bundle.sources) == 1
    assert bundle.sources[0].provider == "musicbrainz"
    assert "test-mbid-123" in bundle.sources[0].url


@pytest.mark.asyncio
async def test_search_recordings(mock_service):
    """测试搜索 Recording"""
    mock_service._client.get = AsyncMock(return_value={
        "recordings": [
            {
                "id": "recording-mbid",
                "title": "Nude",
                "score": 95,
                "length": 260000,
                "artist-credit": [{"name": "Radiohead", "joinphrase": ""}],
                "first-release-date": "2007-10-10",
                "releases": [],
            }
        ]
    })

    results = await mock_service.search_recordings("Nude", "Radiohead")

    assert len(results) == 1
    assert results[0].recording_mbid == "recording-mbid"
    assert results[0].title == "Nude"
    assert results[0].score == 95


@pytest.mark.asyncio
async def test_search_recordings_empty_title(mock_service):
    """测试空标题搜索"""
    results = await mock_service.search_recordings("", "Radiohead")

    assert len(results) == 0
    mock_service._client.get.assert_not_called()


@pytest.mark.asyncio
async def test_search_recordings_api_error(mock_service):
    """测试 API 错误"""
    mock_service._client.get = AsyncMock(side_effect=Exception("API Error"))

    results = await mock_service.search_recordings("Nude", "Radiohead")

    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_recording_metadata(mock_service, sample_metadata):
    """测试获取 Recording 详情"""
    mock_service._client.get = AsyncMock(return_value={
        "id": "test-mbid-123",
        "title": "Nude",
        "length": 260000,
        "artist-credit": [
            {"artist": {"id": "artist-mbid", "name": "Radiohead", "sort-name": "Radiohead"}}
        ],
        "releases": [
            {
                "id": "release-mbid",
                "title": "In Rainbows",
                "date": "2007-10-10",
                "country": "GB",
            }
        ],
        "isrcs": ["GBAHT0600101"],
        "genres": [{"name": "alternative rock", "count": 50}],
        "tags": [],
        "relations": [],
    })
    mock_service._client.get_cover_art = AsyncMock(return_value=None)

    metadata = await mock_service.get_recording_metadata("test-mbid-123")

    assert metadata is not None
    assert metadata.recording_mbid == "test-mbid-123"
    assert metadata.title == "Nude"


@pytest.mark.asyncio
async def test_get_recording_metadata_enriches_release(mock_service):
    """测试 Recording 详情会补充 Release 厂牌信息"""
    mock_service._client.get = AsyncMock(side_effect=[
        {
            "id": "test-mbid-123",
            "title": "Nude",
            "artist-credit": [
                {"artist": {"id": "artist-mbid", "name": "Radiohead"}}
            ],
            "releases": [{"id": "release-mbid", "title": "In Rainbows"}],
            "isrcs": [],
            "genres": [],
            "tags": [],
            "relations": [],
        },
        {
            "id": "release-mbid",
            "title": "In Rainbows",
            "date": "2007-10-10",
            "country": "GB",
            "status": "Official",
            "barcode": "634904032428",
            "label-info": [{"label": {"name": "XL Recordings"}}],
        },
    ])
    mock_service._client.get_cover_art = AsyncMock(return_value=None)

    metadata = await mock_service.get_recording_metadata("test-mbid-123")

    assert metadata is not None
    assert metadata.releases[0].date == "2007-10-10"
    assert metadata.releases[0].label_names == ["XL Recordings"]


@pytest.mark.asyncio
async def test_search_wikipedia_artist_delegates(mock_service):
    """测试 Wikipedia 艺术家资料代理"""
    background = ArtistBackground(artist="Radiohead", title="Radiohead")
    mock_service._external.search_wikipedia_artist = AsyncMock(return_value=background)

    result = await mock_service.search_wikipedia_artist("Radiohead")

    assert result == background


@pytest.mark.asyncio
async def test_get_recording_metadata_not_found(mock_service):
    """测试 Recording 不存在"""
    from mylody.evidence.client import NotFoundError
    mock_service._client.get = AsyncMock(side_effect=NotFoundError("Not found"))

    metadata = await mock_service.get_recording_metadata("nonexistent-mbid")

    assert metadata is None


@pytest.mark.asyncio
async def test_get_recording_metadata_empty_mbid(mock_service):
    """测试空 MBID"""
    metadata = await mock_service.get_recording_metadata("")

    assert metadata is None
    mock_service._client.get.assert_not_called()


def test_make_cache_key():
    """测试缓存键生成"""
    service = EvidenceService()

    key1 = service._make_cache_key("search", title="Nude", artist="Radiohead")
    key2 = service._make_cache_key("search", title="Nude", artist="Radiohead")
    key3 = service._make_cache_key("search", title="Nude", artist="Thom Yorke")

    assert key1 == key2
    assert key1 != key3
    assert key1.startswith("search:")
