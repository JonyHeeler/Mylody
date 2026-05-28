"""乐评路由：提供乐评查询和刷新接口（Phase 2 实现）"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/api/review/refresh")
async def refresh_review() -> dict:
    """强制刷新当前播放歌曲的乐评

    Returns:
        dict: 操作状态（Phase 2 实现阶段返回 not_implemented）
    """
    return {"status": "not_implemented", "message": "乐评功能将在 Phase 2 实现"}


@router.get("/api/review/current")
async def get_current_review() -> dict:
    """获取当前播放歌曲的乐评

    Returns:
        dict: 乐评数据（Phase 2 实现阶段返回空）
    """
    return {"status": "not_implemented", "review": None}
