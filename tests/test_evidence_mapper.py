"""Evidence Mapper 单元测试"""

import pytest

from mylody.evidence.mapper import (
    map_artist_credit,
    map_cover_art,
    map_genre,
    map_recording_detail,
    map_recording_search_result,
    map_release,
)


def test_map_artist_credit():
    """测试映射艺术家信息"""
    data = {
        "artist": {
            "id": "test-mbid-123",
            "name": "Radiohead",
            "sort-name": "Radiohead",
            "disambiguation": "UK rock band",
        },
        "joinphrase": "",
    }

    result = map_artist_credit(data)

    assert result.mbid == "test-mbid-123"
    assert result.name == "Radiohead"
    assert result.sort_name == "Radiohead"
    assert result.disambiguation == "UK rock band"


def test_map_artist_credit_empty():
    """测试映射空艺术家信息"""
    data = {}

    result = map_artist_credit(data)

    assert result.mbid == ""
    assert result.name == ""


def test_map_genre():
    """测试映射流派"""
    data = {"name": "rock", "count": 42}

    result = map_genre(data)

    assert result.name == "rock"
    assert result.count == 42


def test_map_genre_missing_fields():
    """测试映射缺失字段的流派"""
    data = {"name": "electronic"}

    result = map_genre(data)

    assert result.name == "electronic"
    assert result.count == 0


def test_map_release():
    """测试映射发行版本"""
    data = {
        "id": "release-mbid",
        "title": "OK Computer",
        "date": "1997-05-21",
        "country": "GB",
        "status": "Official",
        "barcode": "0724385523523",
        "label-info": [
            {"label": {"name": "Parlophone"}},
            {"label": {"name": "Capitol"}},
        ],
    }

    result = map_release(data)

    assert result.mbid == "release-mbid"
    assert result.title == "OK Computer"
    assert result.date == "1997-05-21"
    assert result.country == "GB"
    assert result.status == "Official"
    assert result.barcode == "0724385523523"
    assert "Parlophone" in result.label_names
    assert "Capitol" in result.label_names


def test_map_release_no_labels():
    """测试映射无厂牌的发行版本"""
    data = {
        "id": "release-mbid",
        "title": "In Rainbows",
        "date": "2007-10-10",
    }

    result = map_release(data)

    assert result.mbid == "release-mbid"
    assert result.title == "In Rainbows"
    assert result.label_names == []


def test_map_recording_search_result():
    """测试映射搜索结果"""
    data = {
        "id": "recording-mbid",
        "title": "Nude",
        "score": 95,
        "length": 260000,
        "artist-credit": [
            {"name": "Radiohead", "joinphrase": ""},
        ],
        "first-release-date": "2007-10-10",
        "releases": [
            {
                "id": "release-mbid",
                "title": "In Rainbows",
                "date": "2007-10-10",
                "country": "GB",
            }
        ],
    }

    result = map_recording_search_result(data)

    assert result.recording_mbid == "recording-mbid"
    assert result.title == "Nude"
    assert result.score == 95
    assert result.length_ms == 260000
    assert result.artist_credit == "Radiohead"
    assert result.first_release_date == "2007-10-10"
    assert len(result.releases) == 1
    assert result.releases[0]["mbid"] == "release-mbid"


def test_map_recording_search_result_multiple_artists():
    """测试映射多艺术家搜索结果"""
    data = {
        "id": "recording-mbid",
        "title": "Something",
        "score": 90,
        "artist-credit": [
            {"name": "Radiohead", "joinphrase": " feat. "},
            {"name": "Thom Yorke", "joinphrase": ""},
        ],
        "releases": [],
    }

    result = map_recording_search_result(data)

    assert result.artist_credit == "Radiohead feat. Thom Yorke"


def test_map_recording_detail():
    """测试映射 Recording 详情"""
    data = {
        "id": "recording-mbid",
        "title": "Nude",
        "length": 260000,
        "artist-credit": [
            {"artist": {"id": "artist-mbid", "name": "Radiohead", "sort-name": "Radiohead"}},
        ],
        "releases": [
            {
                "id": "release-mbid",
                "title": "In Rainbows",
                "date": "2007-10-10",
                "country": "GB",
                "status": "Official",
            }
        ],
        "isrcs": ["GBAHT0600101"],
        "genres": [{"name": "alternative rock", "count": 50}],
        "tags": [{"name": "art rock", "count": 30}, {"name": "experimental", "count": 25}],
        "relations": [
            {
                "type": "wikidata",
                "url": {"resource": "https://www.wikidata.org/wiki/Q123456"},
            }
        ],
    }

    result = map_recording_detail(data)

    assert result.recording_mbid == "recording-mbid"
    assert result.title == "Nude"
    assert result.length_ms == 260000
    assert len(result.artists) == 1
    assert result.artists[0].name == "Radiohead"
    assert len(result.releases) == 1
    assert result.releases[0].title == "In Rainbows"
    assert "GBAHT0600101" in result.isrcs
    assert len(result.genres) == 1
    assert result.genres[0].name == "alternative rock"
    assert len(result.tags) == 2
    assert len(result.external_urls) == 1
    assert result.external_urls[0]["url"] == "https://www.wikidata.org/wiki/Q123456"


def test_map_cover_art():
    """测试映射封面图"""
    data = {
        "images": [
            {
                "front": True,
                "image": "https://coverartarchive.org/release/123/front.jpg",
                "thumbnails": {
                    "250": "https://coverartarchive.org/release/123/front-250.jpg",
                    "500": "https://coverartarchive.org/release/123/front-500.jpg",
                    "1200": "https://coverartarchive.org/release/123/front-1200.jpg",
                },
            }
        ]
    }

    result = map_cover_art(data)

    assert result.image == "https://coverartarchive.org/release/123/front.jpg"
    assert result.thumbnail_250 == "https://coverartarchive.org/release/123/front-250.jpg"
    assert result.thumbnail_500 == "https://coverartarchive.org/release/123/front-500.jpg"
    assert result.thumbnail_1200 == "https://coverartarchive.org/release/123/front-1200.jpg"


def test_map_cover_art_no_front():
    """测试映射无 front 标记的封面图"""
    data = {
        "images": [
            {
                "front": False,
                "image": "https://coverartarchive.org/release/123/back.jpg",
                "thumbnails": {},
            },
            {
                "front": True,
                "image": "https://coverartarchive.org/release/123/front.jpg",
                "thumbnails": {"250": "https://coverartarchive.org/release/123/front-250.jpg"},
            },
        ]
    }

    result = map_cover_art(data)

    assert result.image == "https://coverartarchive.org/release/123/front.jpg"
    assert result.thumbnail_250 == "https://coverartarchive.org/release/123/front-250.jpg"


def test_map_cover_art_empty():
    """测试映射空封面图"""
    data = {"images": []}

    result = map_cover_art(data)

    assert result.image == ""
    assert result.thumbnail_250 == ""


def test_map_cover_art_no_images():
    """测试映射无图片数据"""
    data = {}

    result = map_cover_art(data)

    assert result.image == ""
