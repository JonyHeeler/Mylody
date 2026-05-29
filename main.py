"""Mylody 入口文件：启动 FastAPI 服务和媒体监听"""

import argparse
import asyncio
import logging
import threading
import sys

import uvicorn

from mylody.cache import CacheManager
from mylody.config import Config
from mylody.logger import setup_logger
from mylody.server.app import create_app
from mylody.listener import MediaListener
from mylody.types import MediaInfo
from mylody.utils.paths import get_cache_dir


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Mylody - Windows 音乐意评工具")
    parser.add_argument("--port", type=int, default=0, help="服务端口")
    parser.add_argument("--config", type=str, default="", help="配置文件路径")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘")
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

    db_path = config.get("cache.db_path", "") or str(get_cache_dir() / "reviews.db")
    cache_ttl_days = config.get("cache.cache_ttl_days", 0)
    cache_manager = CacheManager(db_path=db_path, cache_ttl_days=cache_ttl_days)
    logger.info("缓存已初始化: %s (TTL: %d 天)", db_path, cache_ttl_days)

    app = create_app()
    app.state.config = config
    app.state.ai_client = ai_client
    app.state.cache_manager = cache_manager
    app.state.current_review = None
    app.state.current_track_info = None
    app.state.is_generating = False

    async def on_track_change(info: MediaInfo) -> None:
        """曲目变化时的回调：先查缓存，未命中再调用 AI"""
        app.state.current_track = info.to_dict()
        app.state.current_track_info = info
        logger.info("🎵 正在播放: %s - %s", info.title, info.artist)

        cached = cache_manager.get(info.artist, info.title)
        if cached:
            app.state.current_review = cached
            app.state.is_generating = False
            logger.info("✅ 缓存命中，直接使用: %s", cached.summary)
            return

        app.state.is_generating = True
        try:
            review = await ai_client.generate_review(info)
            if review:
                app.state.current_review = review
                cache_manager.put(
                    info.artist, info.title, info.album, review,
                    model=config.get("ai.model", ""),
                )
                logger.info("✅ 乐评生成成功: %s", review.summary)
            else:
                app.state.current_review = None
                logger.warning("⚠️ 乐评生成失败")
        finally:
            app.state.is_generating = False

    listener = MediaListener(config, on_track_change)
    start_listener(app, listener)

    port = args.port or config.get("server.port", 5800)
    host = config.get("server.host", "127.0.0.1")
    logger.info("Mylody 启动于 http://%s:%s", host, port)

    enable_tray = not args.no_tray and sys.platform == "win32"
    tray_icon = None

    if enable_tray:
        try:
            from mylody.tray import TrayIcon

            def on_tray_exit():
                logger.info("用户通过托盘退出")
                sys.exit(0)

            tray_icon = TrayIcon(port=port, on_exit=on_tray_exit)
            tray_icon.start()
            logger.info("系统托盘已启动")
        except Exception as e:
            logger.warning("系统托盘启动失败: %s", e)

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
