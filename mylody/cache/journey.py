"""音乐旅程数据读取：从乐评缓存整理可供 AI 分析的时间线"""

import json
import logging

from mylody.ai.guardrails import normalize_review_payload

logger = logging.getLogger("mylody.cache.journey")


def list_review_journey(cache_manager, limit: int = 30) -> list[dict]:
    """读取带生成时间的乐评时间线。

    Args:
        cache_manager: 已初始化的乐评缓存管理器
        limit: 最多读取多少条缓存乐评

    Returns:
        list[dict]: 按生成时间升序排列的乐评摘要和正文
    """
    try:
        rows = cache_manager._db.conn.execute(
            """SELECT title, artist, album, review_json, created_at, updated_at
               FROM reviews
               ORDER BY COALESCE(created_at, updated_at) ASC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    except Exception as e:
        logger.error("音乐旅程读取失败: %s", e)
        return []

    return [_build_journey_item(row) for row in rows]


def _build_journey_item(row) -> dict:
    """Build one normalized journey item from a SQLite row."""
    title, artist, album, review_json, created_at, updated_at = row
    review = _load_review_payload(review_json)
    return {
        "title": title or "未知歌曲",
        "artist": artist or "未知艺术家",
        "album": album or "",
        "generated_at": created_at or updated_at or "",
        "emotion": review.get("emotion", ""),
        "rating": review.get("rating"),
        "quote": review.get("quote", ""),
        "review": _compact_text(review.get("content", ""), limit=360),
    }


def _load_review_payload(review_json: str) -> dict:
    """Parse and normalize one cached review payload."""
    try:
        data = json.loads(review_json)
        return normalize_review_payload(data)
    except (json.JSONDecodeError, TypeError):
        return {}


def _compact_text(text: str, limit: int) -> str:
    """Compress cached review text for the personality prompt."""
    if not isinstance(text, str):
        return ""
    compacted = " ".join(text.split())
    return compacted[:limit]
