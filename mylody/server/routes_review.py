"""乐评路由：提供乐评查询和刷新接口"""

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger("mylody.server.review")

router = APIRouter()


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
    """强制刷新当前播放歌曲的乐评

    Returns:
        dict: 操作状态和乐评数据
    """
    ai_client = getattr(request.app.state, "ai_client", None)
    track_info = getattr(request.app.state, "current_track_info", None)

    if ai_client is None:
        return {"status": "error", "message": "AI 客户端未初始化"}

    if track_info is None:
        return {"status": "error", "message": "当前无播放曲目"}

    review = await ai_client.generate_review(track_info)

    if review is None:
        return {"status": "error", "message": "乐评生成失败，请查看日志"}

    request.app.state.current_review = review
    logger.info("乐评已刷新: %s - %s", track_info.artist, track_info.title)

    return {"status": "ok", "review": review.to_dict()}
