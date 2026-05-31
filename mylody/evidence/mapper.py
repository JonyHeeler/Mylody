"""数据映射器：将 MusicBrainz 原始数据转换为内部类型"""

from datetime import datetime, timezone

from mylody.evidence.types import (
    ArtistInfo,
    CoverArt,
    GenreTag,
    MusicMetadata,
    MusicSearchResult,
    ReleaseInfo,
)


def map_artist_credit(artist_credit: dict) -> ArtistInfo:
    """映射艺术家信息

    Args:
        artist_credit: MusicBrainz artist-credit 对象

    Returns:
        ArtistInfo: 艺术家信息
    """
    artist = artist_credit.get("artist", {})
    return ArtistInfo(
        mbid=artist.get("id", ""),
        name=artist.get("name", ""),
        sort_name=artist.get("sort-name", ""),
        disambiguation=artist.get("disambiguation", ""),
    )


def map_genre(genre: dict) -> GenreTag:
    """映射流派/标签

    Args:
        genre: MusicBrainz genre/tag 对象

    Returns:
        GenreTag: 流派/标签
    """
    return GenreTag(
        name=genre.get("name", ""),
        count=genre.get("count", 0),
    )


def map_release(release: dict) -> ReleaseInfo:
    """映射发行版本

    Args:
        release: MusicBrainz release 对象

    Returns:
        ReleaseInfo: 发行版本信息
    """
    label_names = []
    for label_info in release.get("label-info", []):
        label = label_info.get("label")
        if label and label.get("name"):
            label_names.append(label["name"])

    return ReleaseInfo(
        mbid=release.get("id", ""),
        title=release.get("title", ""),
        date=release.get("date", ""),
        country=release.get("country", ""),
        status=release.get("status", ""),
        barcode=release.get("barcode", ""),
        label_names=label_names,
    )


def map_recording_search_result(recording: dict) -> MusicSearchResult:
    """映射搜索结果

    Args:
        recording: MusicBrainz recording 搜索结果对象

    Returns:
        MusicSearchResult: 搜索结果
    """
    artist_credit_text = ""
    releases = []

    for ac in recording.get("artist-credit", []):
        artist_credit_text += ac.get("name", "") + ac.get("joinphrase", "")

    for release in recording.get("releases", []):
        releases.append({
            "mbid": release.get("id", ""),
            "title": release.get("title", ""),
            "date": release.get("date", ""),
            "country": release.get("country", ""),
        })

    return MusicSearchResult(
        recording_mbid=recording.get("id", ""),
        title=recording.get("title", ""),
        score=recording.get("score", 0),
        length_ms=recording.get("length", 0),
        artist_credit=artist_credit_text.strip(),
        first_release_date=recording.get("first-release-date", ""),
        releases=releases,
    )


def map_recording_detail(data: dict) -> MusicMetadata:
    """映射 Recording 详情

    Args:
        data: MusicBrainz recording detail 响应

    Returns:
        MusicMetadata: 音乐元数据
    """
    artists = []
    for ac in data.get("artist-credit", []):
        artists.append(map_artist_credit(ac))

    releases = []
    for release in data.get("releases", []):
        releases.append(map_release(release))

    genres = [map_genre(g) for g in data.get("genres", [])]
    tags = [map_genre(t) for t in data.get("tags", [])]

    external_urls = []
    for rel in data.get("relations", []):
        url = rel.get("url", {})
        if url.get("resource"):
            external_urls.append({
                "type": rel.get("type", ""),
                "url": url["resource"],
            })

    return MusicMetadata(
        recording_mbid=data.get("id", ""),
        title=data.get("title", ""),
        length_ms=data.get("length", 0),
        artists=artists,
        releases=releases,
        isrcs=data.get("isrcs", []),
        genres=genres,
        tags=tags,
        external_urls=external_urls,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


def map_cover_art(data: dict) -> CoverArt:
    """映射封面图

    Args:
        data: Cover Art Archive 响应

    Returns:
        CoverArt: 封面图信息
    """
    front = None
    for image in data.get("images", []):
        if image.get("front"):
            front = image
            break

    if front is None and data.get("images"):
        front = data["images"][0]

    if front is None:
        return CoverArt()

    thumbnails = front.get("thumbnails", {})
    return CoverArt(
        image=front.get("image", ""),
        thumbnail_250=thumbnails.get("250", thumbnails.get("small", "")),
        thumbnail_500=thumbnails.get("500", thumbnails.get("large", "")),
        thumbnail_1200=thumbnails.get("1200", ""),
    )
