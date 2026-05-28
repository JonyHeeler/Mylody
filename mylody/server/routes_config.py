"""配置路由：提供配置查询接口（脱敏显示）"""

from fastapi import APIRouter, Request

from mylody.utils.sanitize import sanitize_config

router = APIRouter()


@router.get("/api/config")
async def get_config(request: Request) -> dict:
    """返回当前配置（敏感字段已脱敏）

    Returns:
        dict: 脱敏后的配置数据
    """
    config = getattr(request.app.state, "config", None)
    if config is None:
        return {"error": "配置未加载"}
    return sanitize_config(config.data)
