"""缓存管理器：基于 SQLite 的乐评缓存读写、过期检查和统计"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from mylody.cache.db import Database
from mylody.cache.key import normalize_cache_key
from mylody.types import ReviewData

logger = logging.getLogger("mylody.cache.manager")


class CacheManager:
    """乐评缓存管理器

    负责将 AI 生成的乐评持久化到本地 SQLite 数据库，
    支持缓存读写、过期检查和统计。

    Args:
        db_path: 数据库文件路径
        cache_ttl_days: 缓存过期天数，0 表示永不过期
    """

    def __init__(self, db_path: str, cache_ttl_days: int = 0) -> None:
        from pathlib import Path

        self._ttl_days = cache_ttl_days
        self._db = Database(Path(db_path))
        self._db.connect()

    def get(self, artist: str, title: str) -> Optional[ReviewData]:
        """查询缓存中的乐评

        Args:
            artist: 艺术家名称
            title: 歌曲名称

        Returns:
            Optional[ReviewData]: 缓存的乐评，未命中返回 None
        """
        cache_key = normalize_cache_key(artist, title)

        row = self._db.conn.execute(
            "SELECT review_json, updated_at FROM reviews WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

        if row is None:
            logger.debug("缓存未命中: %s", cache_key)
            return None

        review_json, updated_at = row

        if self._is_expired(updated_at):
            logger.debug("缓存已过期: %s", cache_key)
            self._db.conn.execute(
                "DELETE FROM reviews WHERE cache_key = ?", (cache_key,)
            )
            self._db.conn.commit()
            return None

        logger.info("缓存命中: %s", cache_key)
        return self._deserialize_review(review_json)

    def put(
        self,
        artist: str,
        title: str,
        album: str,
        review: ReviewData,
        model: str = "",
    ) -> bool:
        """写入乐评到缓存

        Args:
            artist: 艺术家名称
            title: 歌曲名称
            album: 专辑名称
            review: 乐评数据
            model: AI 模型名称

        Returns:
            bool: 是否写入成功
        """
        cache_key = normalize_cache_key(artist, title)
        review_json = json.dumps(review.to_dict(), ensure_ascii=False)
        now = datetime.utcnow().isoformat()

        try:
            self._db.conn.execute(
                """INSERT INTO reviews (cache_key, title, artist, album, review_json, ai_model, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(cache_key) DO UPDATE SET
                       review_json = excluded.review_json,
                       ai_model = excluded.ai_model,
                       updated_at = excluded.updated_at""",
                (cache_key, title, artist, album, review_json, model, now, now),
            )
            self._db.conn.commit()
            logger.info("缓存写入成功: %s", cache_key)
            return True
        except Exception as e:
            logger.error("缓存写入失败: %s - %s", cache_key, e)
            return False

    def delete(self, artist: str, title: str) -> bool:
        """删除指定歌曲的缓存

        Args:
            artist: 艺术家名称
            title: 歌曲名称

        Returns:
            bool: 是否删除成功
        """
        cache_key = normalize_cache_key(artist, title)

        try:
            cursor = self._db.conn.execute(
                "DELETE FROM reviews WHERE cache_key = ?", (cache_key,)
            )
            self._db.conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("缓存已删除: %s", cache_key)
            return deleted
        except Exception as e:
            logger.error("缓存删除失败: %s - %s", cache_key, e)
            return False

    def stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            dict: 缓存统计数据
        """
        try:
            row = self._db.conn.execute(
                "SELECT COUNT(*) FROM reviews"
            ).fetchone()
            total = row[0] if row else 0
        except Exception:
            total = 0

        return {
            "total": total,
            "ttl_days": self._ttl_days,
            "db_path": str(self._db._db_path),
        }

    def close(self) -> None:
        """关闭缓存管理器，释放数据库连接"""
        self._db.close()

    def _is_expired(self, updated_at: str) -> bool:
        """检查缓存是否过期

        Args:
            updated_at: 缓存更新时间（ISO 8601 格式）

        Returns:
            bool: 是否过期
        """
        if self._ttl_days <= 0:
            return False

        try:
            updated = datetime.fromisoformat(updated_at)
            return updated + timedelta(days=self._ttl_days) < datetime.utcnow()
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _deserialize_review(review_json: str) -> Optional[ReviewData]:
        """反序列化乐评 JSON

        Args:
            review_json: 乐评 JSON 字符串

        Returns:
            Optional[ReviewData]: 反序列化后的乐评数据
        """
        try:
            data = json.loads(review_json)
            return ReviewData(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("缓存数据反序列化失败: %s", e)
            return None
