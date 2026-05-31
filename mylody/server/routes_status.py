"""状态路由：提供服务运行状态和当前播放信息"""

import time

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/status")
async def get_status(request: Request) -> dict:
    """返回服务状态和当前播放信息

    Returns:
        dict: 包含 running、current_track、uptime_seconds 的状态对象
    """
    start_time = getattr(request.app.state, "start_time", time.time())
    current_track = getattr(request.app.state, "current_track", None)

    return {
        "running": True,
        "current_track": current_track,
        "uptime_seconds": round(time.time() - start_time, 1),
        "is_generating": getattr(request.app.state, "is_generating", False),
        "status_events": getattr(request.app.state, "status_events", []),
    }
