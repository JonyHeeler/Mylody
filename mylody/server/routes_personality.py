"""音乐人格路由：根据缓存乐评生成音乐人格和旅程回顾"""

import logging

from fastapi import APIRouter, Request

from mylody.ai.personality import generate_music_personality
from mylody.cache.journey import list_review_journey
from mylody.cache.personality import PersonalityCache
from mylody.server.status_log import add_status

logger = logging.getLogger("mylody.server.personality")

router = APIRouter()


@router.post("/api/personality/generate")
async def generate_personality(request: Request) -> dict:
    """生成音乐人格与音乐旅程回顾。

    Returns:
        dict: 生成状态、分析文本和使用的乐评数量
    """
    ai_client = getattr(request.app.state, "ai_client", None)
    cache_manager = getattr(request.app.state, "cache_manager", None)

    if ai_client is None:
        return {"status": "error", "message": "AI 客户端未初始化"}
    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化"}

    force = request.query_params.get("force", "").lower() in ("1", "true", "yes")
    personality_cache = PersonalityCache(cache_manager)
    latest = personality_cache.latest()
    if latest and not force:
        return {
            "status": "ok",
            "content": latest["content"],
            "count": latest["item_count"],
            "cached": True,
            "id": latest["id"],
            "created_at": latest["created_at"],
        }

    journey = list_review_journey(cache_manager)
    if not journey:
        return {"status": "error", "message": "暂无缓存乐评，先听几首歌再生成吧"}

    add_status(request.app, f"音乐人格: 打包 {len(journey)} 条乐评时间线")
    try:
        content = await generate_music_personality(ai_client, journey)
    except Exception as e:
        logger.exception("音乐人格生成失败: %s", type(e).__name__)
        add_status(request.app, "音乐人格生成失败，详情见后端日志")
        return {"status": "error", "message": "音乐人格生成失败，请查看日志"}

    model = getattr(request.app.state, "config", None)
    model_name = model.get("ai.model", "") if model else ""
    saved = personality_cache.save(content.strip(), len(journey), model_name)
    add_status(request.app, "音乐人格生成成功")
    return {
        "status": "ok",
        "content": saved["content"],
        "count": saved["item_count"],
        "cached": False,
        "id": saved["id"],
        "created_at": saved["created_at"],
    }


@router.get("/api/personality/history")
async def list_personality_history(request: Request) -> dict:
    """列出已保存的音乐人格版本。"""
    cache_manager = getattr(request.app.state, "cache_manager", None)
    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化", "items": []}

    return {"status": "ok", "items": PersonalityCache(cache_manager).list()}


@router.get("/api/personality/history/{personality_id}")
async def get_personality_history(personality_id: int, request: Request) -> dict:
    """读取一个音乐人格全文。"""
    cache_manager = getattr(request.app.state, "cache_manager", None)
    if cache_manager is None:
        return {"status": "error", "message": "缓存未初始化"}

    item = PersonalityCache(cache_manager).get(personality_id)
    if item is None:
        return {"status": "error", "message": "音乐人格不存在"}
    return {"status": "ok", "item": item}
