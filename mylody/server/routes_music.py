"""音乐元数据路由：提供 MusicBrainz 搜索和详情查询接口"""

import logging
import re

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger("mylody.server.music")

MBID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

router = APIRouter()


def _get_evidence_service(request: Request):
    """获取 EvidenceService 实例"""
    service = getattr(request.app.state, "evidence_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Evidence 服务未初始化")
    return service


@router.get("/api/music/search")
async def search_recordings(
    request: Request,
    title: str = Query(..., min_length=1, description="歌曲标题"),
    artist: str = Query("", description="艺术家名称"),
    limit: int = Query(10, ge=1, le=25, description="返回数量"),
) -> dict:
    """搜索 Recording

    Args:
        title: 歌曲标题
        artist: 艺术家名称
        limit: 返回数量限制

    Returns:
        dict: 搜索结果列表
    """
    service = _get_evidence_service(request)
    results = await service.search_recordings(title, artist, limit)

    return {
        "status": "ok",
        "results": [r.to_dict() for r in results],
    }


@router.get("/api/music/recording/{mbid}")
async def get_recording_metadata(request: Request, mbid: str) -> dict:
    """获取 Recording 详情

    Args:
        mbid: Recording MusicBrainz ID

    Returns:
        dict: 音乐元数据
    """
    if not MBID_PATTERN.match(mbid):
        raise HTTPException(status_code=400, detail="无效的 MBID 格式")

    service = _get_evidence_service(request)
    metadata = await service.get_recording_metadata(mbid)

    if metadata is None:
        raise HTTPException(status_code=404, detail="Recording 不存在")

    return {
        "status": "ok",
        "metadata": metadata.to_dict(),
    }


@router.get("/api/music/artist/wikipedia")
async def search_wikipedia_artist(
    request: Request,
    artist: str = Query(..., min_length=1, description="艺术家名称"),
) -> dict:
    """Search Wikipedia artist background."""
    service = _get_evidence_service(request)
    background = await service.search_wikipedia_artist(artist)

    return {
        "status": "ok",
        "background": background.to_dict() if background else None,
    }


@router.get("/api/music/wikipedia/context")
async def search_wikipedia_music_context(
    request: Request,
    title: str = Query(..., min_length=1, description="歌曲标题"),
    artist: str = Query("", description="艺术家名称"),
    album: str = Query("", description="专辑或发行标题"),
) -> dict:
    """Search precise Wikipedia context for song, release and artist."""
    service = _get_evidence_service(request)
    context = await service.search_wikipedia_music_context(title, artist, album)

    return {
        "status": "ok",
        "context": context.to_dict() if context else None,
    }

