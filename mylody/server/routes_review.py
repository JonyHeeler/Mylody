"""乐评路由：提供乐评查询、刷新和缓存统计接口"""

import logging

from fastapi import APIRouter, Request
from mylody.evidence.bundle_formatter import format_ai_evidence
from mylody.evidence.types import EvidenceBundle
from mylody.server.status_log import add_status

logger = logging.getLogger("mylody.server.review")

router = APIRouter()


async def _fetch_evidence_bundle(request: Request, track_info) -> dict:
    """Fetch MusicBrainz evidence for manual refresh."""
    evidence_service = getattr(request.app.state, "evidence_service", None)
    if evidence_service is None:
        return {"confidence": 0.0}

    try:
        results = await evidence_service.search_recordings(
            track_info.title, track_info.artist, limit=3
        )
        bundle = EvidenceBundle(
            track_title=track_info.title,
            artist=track_info.artist,
            album=track_info.album,
        )
        if results:
            best = results[0]
            metadata = await evidence_service.get_recording_metadata(best.recording_mbid)
            if metadata is not None:
                bundle = evidence_service.build_evidence(
                    track_info.title,
                    track_info.artist,
                    track_info.album,
                    metadata,
                    search_score=best.score,
                )
            else:
                add_status(request.app, '"MusicBrainz" 未启用或不可用，已跳过')
        else:
            add_status(request.app, '"MusicBrainz" 未启用或不可用，已跳过')

        wikipedia_context = await evidence_service.search_wikipedia_music_context(
            track_info.title, track_info.artist, track_info.album
        )
        if wikipedia_context is None:
            add_status(request.app, '"Wikipedia" 未启用或不可用，已跳过')
        return format_ai_evidence(
            bundle,
            wikipedia_context=wikipedia_context,
        )
    except Exception as e:
        logger.warning("刷新乐评获取 MusicBrainz 证据失败: %s", e)
        add_status(request.app, '"外部证据" 未启用或不可用，已跳过')
        return {"confidence": 0.0}


@router.get("/api/review/current")
async def get_current_review(request: Request) -> dict:
    """获取当前播放歌曲的乐评

    Returns:
        dict: 乐评数据，无乐评时返回 None
    """
    review = getattr(request.app.state, "current_review", None)
    track = getattr(request.app.state, "current_track", None)

    return {
        "status": "ok",
        "track": track,
        "review": review.to_dict() if review else None,
    }


@router.post("/api/review/refresh")
async def refresh_review(request: Request) -> dict:
    """强制刷新当前播放歌曲的乐评（跳过缓存，重新生成并覆盖缓存）

    Returns:
        dict: 操作状态和乐评数据
    """
    ai_client = getattr(request.app.state, "ai_client", None)
    track_info = getattr(request.app.state, "current_track_info", None)
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if ai_client is None:
        return {"status": "error", "message": "AI 客户端未初始化"}

    if track_info is None or not track_info.is_playable_track():
        return {"status": "error", "message": "当前无播放曲目"}

    config = getattr(request.app.state, "config", None)
    model = config.get("ai.model", "") if config else ""

    add_status(request.app, "手动刷新: 查询 MusicBrainz")
    evidence_bundle = await _fetch_evidence_bundle(request, track_info)
    if evidence_bundle.get("known_facts"):
        add_status(request.app, f"手动刷新: MusicBrainz 命中，置信度 {evidence_bundle.get('confidence', 0):.2f}")
    else:
        add_status(request.app, "手动刷新: MusicBrainz 未命中，降级为曲目元数据")
    add_status(request.app, "手动刷新: 请求 AI 生成乐评")
    review = await ai_client.generate_review(track_info, evidence_bundle=evidence_bundle)

    if review is None:
        add_status(request.app, "手动刷新失败: AI 未返回有效乐评")
        return {"status": "error", "message": "乐评生成失败，请查看日志"}

    request.app.state.current_review = review

    if cache_manager:
        cache_manager.put(
            track_info.artist, track_info.title, track_info.album,
            review, model=model,
        )

    logger.info("乐评已刷新: %s - %s", track_info.artist, track_info.title)
    add_status(request.app, "手动刷新成功，已更新乐评")

    return {"status": "ok", "review": review.to_dict()}


@router.get("/api/cache/stats")
async def get_cache_stats(request: Request) -> dict:
    """获取缓存统计信息

    Returns:
        dict: 缓存统计数据
    """
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化"}

    return {"status": "ok", "data": cache_manager.stats()}


@router.get("/api/cache/reviews")
async def list_cached_reviews(request: Request) -> dict:
    """列出已缓存乐评。"""
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化", "items": []}

    return {"status": "ok", "items": cache_manager.list_reviews()}


@router.delete("/api/cache/reviews")
async def clear_cached_reviews(request: Request) -> dict:
    """清空全部缓存乐评。"""
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化"}

    deleted = cache_manager.clear()
    request.app.state.current_review = None
    add_status(request.app, f"已清空缓存乐评: {deleted} 条")
    return {"status": "ok", "deleted": deleted}


@router.delete("/api/cache/reviews/{cache_key:path}")
async def delete_cached_review(cache_key: str, request: Request) -> dict:
    """删除指定缓存乐评。"""
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化"}

    deleted = cache_manager.delete_by_key(cache_key)
    if not deleted:
        return {"status": "error", "message": "缓存不存在或删除失败"}

    add_status(request.app, f"已删除缓存乐评: {cache_key}")
    return {"status": "ok"}
