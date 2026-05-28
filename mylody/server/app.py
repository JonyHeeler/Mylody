"""FastAPI 应用工厂：创建应用实例，注册路由和静态文件"""

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mylody.server.routes_status import router as status_router
from mylody.server.routes_review import router as review_router
from mylody.server.routes_config import router as config_router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例

    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(
        title="Mylody",
        description="Windows 桌面音乐乐评工具",
        version="0.1.0",
    )

    app.state.start_time = time.time()
    app.state.current_track = None

    app.include_router(status_router)
    app.include_router(review_router)
    app.include_router(config_router)

    web_dir = Path(__file__).parent.parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app
