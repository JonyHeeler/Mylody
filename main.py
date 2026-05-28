"""Mylody 入口文件：启动 FastAPI 服务和媒体监听"""

import argparse
import asyncio
import logging
import threading

import uvicorn

from mylody.config import Config
from mylody.logger import setup_logger
from mylody.server.app import create_app
from mylody.listener import MediaListener
from mylody.types import MediaInfo


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Mylody - Windows 音乐意评工具")
    parser.add_argument("--port", type=int, default=0, help="服务端口")
    parser.add_argument("--config", type=str, default="", help="配置文件路径")
    return parser.parse_args()


def start_listener(app, listener: MediaListener) -> None:
    """在后台线程启动媒体监听"""
    def run():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(listener.start())
        loop.run_forever()

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

    from mylody.ai import AIClient

    ai_client = AIClient(config)

    app = create_app()
    app.state.config = config
    app.state.ai_client = ai_client
    app.state.current_review = None
    app.state.current_track_info = None

    async def on_track_change(info: MediaInfo) -> None:
        """曲目变化时的回调：更新状态并生成乐评"""
        app.state.current_track = info.to_dict()
        app.state.current_track_info = info
        logger.info("🎵 正在播放: %s - %s", info.title, info.artist)

        review = await ai_client.generate_review(info)
        if review:
            app.state.current_review = review
            logger.info("✅ 乐评生成成功: %s", review.summary)
        else:
            app.state.current_review = None
            logger.warning("⚠️ 乐评生成失败")

    listener = MediaListener(config, on_track_change)
    start_listener(app, listener)

    port = args.port or config.get("server.port", 5800)
    host = config.get("server.host", "127.0.0.1")
    logger.info("Mylody 启动于 http://%s:%s", host, port)

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
