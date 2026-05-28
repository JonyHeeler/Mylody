"""Mylody 入口文件：启动 FastAPI 服务和媒体监听"""

import argparse
import asyncio
import logging
import threading

import uvicorn

from mylody.config import Config
from mylody.logger import setup_logger
from mylody.server.app import create_app
from mylody.listener.media_session import MediaSessionManager


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Mylody - Windows 音乐意评工具")
    parser.add_argument("--port", type=int, default=0, help="服务端口")
    parser.add_argument("--config", type=str, default="", help="配置文件路径")
    return parser.parse_args()


def start_listener(app, media_mgr: MediaSessionManager, poll_interval: int) -> None:
    """在后台线程启动媒体监听"""
    async def poll_loop():
        await media_mgr.initialize()
        while True:
            info = await media_mgr.get_current_info()
            app.state.current_track = info.to_dict() if info else None
            await asyncio.sleep(poll_interval)

    def run():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(poll_loop())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def main() -> None:
    """启动 Mylody 服务"""
    args = parse_args()
    config = Config(args.config or None)
    setup_logger(
        level=config.get("logging.level", "INFO"),
        max_file_size_mb=config.get("logging.max_file_size_mb", 5),
        backup_count=config.get("logging.backup_count", 3),
    )
    logger = logging.getLogger("mylody")

    warnings = config.validate()
    for w in warnings:
        logger.warning(w)

    app = create_app()
    app.state.config = config

    media_mgr = MediaSessionManager()
    poll_interval = config.get("listener.poll_interval_seconds", 2)
    start_listener(app, media_mgr, poll_interval)

    port = args.port or config.get("server.port", 5800)
    host = config.get("server.host", "127.0.0.1")
    logger.info("Mylody 启动于 http://%s:%s", host, port)

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
