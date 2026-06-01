"""Mylody 入口文件：启动 FastAPI 服务和媒体监听"""

import argparse
import asyncio
import logging
import threading
import sys

import uvicorn

from mylody.cache import CacheManager
from mylody.config import Config
from mylody.evidence.bundle_formatter import format_ai_evidence
from mylody.evidence.service import EvidenceService
from mylody.evidence.types import EvidenceBundle
from mylody.logger import setup_logger
from mylody.server.app import create_app
from mylody.server.status_log import add_status
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
    evidence_service = EvidenceService(
        wikipedia_language=config.get("evidence.wikipedia_language", "en"),
    )
    logger.info("MusicBrainz Evidence 服务已初始化")

    app = create_app()
    add_status(app, f"服务启动，配置文件: {config.path}")
    add_status(app, f"AI 模型: {config.get('ai.model', '')}")
    add_status(app, "MusicBrainz 已启用；联网搜索仍禁用")
    app.state.config = config
    app.state.ai_client = ai_client
    app.state.cache_manager = cache_manager
    app.state.evidence_service = evidence_service
    app.state.current_review = None
    app.state.current_track_info = None
    app.state.is_generating = False

    async def on_track_change(info: MediaInfo) -> None:
        """曲目变化时的回调：先查缓存，未命中再调用 AI"""
        if not info.is_playable_track():
            on_track_clear()
            return

        app.state.current_track = info.to_dict()
        app.state.current_track_info = info
        logger.info("🎵 正在播放: %s - %s", info.title, info.artist)
        add_status(app, f"读取新歌: {info.title} - {info.artist}")

        add_status(app, "查询本地缓存")
        cached = cache_manager.get(info.artist, info.title)
        if cached:
            app.state.current_review = cached
            app.state.is_generating = False
            logger.info("✅ 缓存命中，直接使用: %s", cached.content[:50])
            add_status(app, "缓存命中，已加载乐评")
            return

        app.state.is_generating = True
        add_status(app, "缓存未命中，查询 MusicBrainz")
        try:
            evidence_bundle = await _fetch_evidence_bundle(info)
            if evidence_bundle.get("known_facts"):
                add_status(app, f"MusicBrainz 命中，置信度 {evidence_bundle.get('confidence', 0):.2f}")
            else:
                add_status(app, "MusicBrainz 未命中，降级为曲目元数据")
            add_status(app, "请求 AI 生成乐评")
            review = await ai_client.generate_review(info, evidence_bundle=evidence_bundle)
            if review:
                app.state.current_review = review
                cache_manager.put(
                    info.artist, info.title, info.album, review,
                    model=config.get("ai.model", ""),
                )
                logger.info("✅ 乐评生成成功: %s", review.content[:50])
                add_status(app, "AI 乐评生成成功，已写入缓存")
            else:
                app.state.current_review = None
                logger.warning("⚠️ 乐评生成失败")
                add_status(app, "AI 乐评生成失败，详情见后端日志")
        finally:
            app.state.is_generating = False
            add_status(app, "生成状态结束")

    async def _fetch_evidence_bundle(info: MediaInfo) -> dict:
        """Fetch MusicBrainz evidence; failure must not block AI generation."""
        try:
            results = await evidence_service.search_recordings(
                info.title, info.artist, limit=3
            )
            bundle = EvidenceBundle(
                track_title=info.title,
                artist=info.artist,
                album=info.album,
            )
            if results:
                best = results[0]
                metadata = await evidence_service.get_recording_metadata(
                    best.recording_mbid
                )
                if metadata is not None:
                    bundle = evidence_service.build_evidence(
                        info.title,
                        info.artist,
                        info.album,
                        metadata,
                        search_score=best.score,
                    )
                else:
                    add_status(app, '"MusicBrainz" 未启用或不可用，已跳过')
            else:
                add_status(app, '"MusicBrainz" 未启用或不可用，已跳过')

            wikipedia_context = await evidence_service.search_wikipedia_music_context(
                info.title, info.artist, info.album
            )
            if wikipedia_context is None:
                add_status(app, '"Wikipedia" 未启用或不可用，已跳过')
            return format_ai_evidence(
                bundle,
                wikipedia_context=wikipedia_context,
            )
        except Exception as e:
            logger.warning("MusicBrainz 证据获取失败: %s", e)
            add_status(app, '"外部证据" 未启用或不可用，已跳过')
            return {"confidence": 0.0}

    def on_track_clear() -> None:
        """无有效播放曲目时清空当前状态"""
        app.state.current_track = None
        app.state.current_track_info = None
        app.state.current_review = None
        app.state.is_generating = False
        add_status(app, "当前无有效播放曲目")

    listener = MediaListener(config, on_track_change, on_track_clear=on_track_clear)
    start_listener(app, listener)

    port = args.port or config.get("server.port", 5800)
    host = config.get("server.host", "127.0.0.1")
    logger.info("Mylody 启动于 http://%s:%s", host, port)
    add_status(app, f"Web 服务监听: http://{host}:{port}")

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
