"""缓存管理器：基于 SQLite 的乐评缓存读写、过期检查和统计"""

import json
import logging
from datetime import datetime, timedelta
from dataclasses import fields
from typing import Optional

from mylody.cache.db import Database
from mylody.cache.key import normalize_cache_key
from mylody.ai.guardrails import normalize_review_payload
from mylody.types import ReviewData

logger = logging.getLogger("mylody.cache.manager")

CURRENT_SCHEMA_VERSION = "review_v2"


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
            self._delete_cache_key(cache_key)
            return None

        if not self._check_schema_version(review_json, cache_key):
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

    def list_reviews(self, limit: int = 200) -> list[dict]:
        """列出已缓存乐评摘要，按更新时间倒序。"""
        try:
            rows = self._db.conn.execute(
                """SELECT cache_key, title, artist, album, review_json, ai_model, created_at, updated_at
                   FROM reviews
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        except Exception as e:
            logger.error("缓存列表读取失败: %s", e)
            return []

        items = []
        for row in rows:
            cache_key, title, artist, album, review_json, model, created_at, updated_at = row
            review = self._deserialize_review(review_json)
            fallback = self._extract_review_summary(review_json)
            items.append({
                "cache_key": cache_key,
                "title": title,
                "artist": artist or "",
                "album": album or "",
                "model": model or "",
                "created_at": created_at,
                "updated_at": updated_at,
                "rating": review.rating if review else fallback.get("rating"),
                "emotion": review.emotion if review else fallback.get("emotion", ""),
                "excerpt": (review.content[:120] if review else fallback.get("excerpt", "")),
            })
        return items

    def delete_by_key(self, cache_key: str) -> bool:
        """按缓存键删除乐评。"""
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

    def get_by_key(self, cache_key: str) -> Optional[dict]:
        """按缓存键读取完整乐评。"""
        try:
            row = self._db.conn.execute(
                """SELECT cache_key, title, artist, album, review_json, ai_model,
                          created_at, updated_at
                   FROM reviews
                   WHERE cache_key = ?""",
                (cache_key,),
            ).fetchone()
        except Exception as e:
            logger.error("缓存详情读取失败: %s", e)
            return None

        if row is None:
            return None

        cache_key, title, artist, album, review_json, model, created_at, updated_at = row
        review = self._deserialize_review(review_json)
        try:
            fallback = normalize_review_payload(json.loads(review_json))
        except (json.JSONDecodeError, TypeError):
            fallback = {}
        return {
            "cache_key": cache_key,
            "title": title,
            "artist": artist or "",
            "album": album or "",
            "model": model or "",
            "created_at": created_at,
            "updated_at": updated_at,
            "review": review.to_dict() if review else fallback,
        }

    def clear(self) -> int:
        """清空全部缓存，返回删除条数。"""
        try:
            cursor = self._db.conn.execute("DELETE FROM reviews")
            self._db.conn.commit()
            deleted = cursor.rowcount if cursor.rowcount >= 0 else 0
            logger.info("缓存已清空: %d 条", deleted)
            return deleted
        except Exception as e:
            logger.error("清空缓存失败: %s", e)
            return 0

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

    def _check_schema_version(self, review_json: str, cache_key: str) -> bool:
        """检查缓存的 schema 版本是否匹配

        Args:
            review_json: 缓存的 JSON 字符串
            cache_key: 缓存键

        Returns:
            bool: 版本匹配返回 True
        """
        try:
            data = json.loads(review_json)
            version = data.get("schema_version")
        except (json.JSONDecodeError, TypeError):
            logger.warning("缓存 JSON 解析失败，视为版本不匹配: %s", cache_key)
            self._delete_cache_key(cache_key)
            return False

        if version != CURRENT_SCHEMA_VERSION:
            normalized = normalize_review_payload(data)
            if normalized.get("schema_version") == CURRENT_SCHEMA_VERSION:
                logger.info("旧版缓存可兼容读取: %s", cache_key)
                return True

            logger.info(
                "缓存 schema 版本不匹配 (缓存: %s, 当前: %s): %s",
                version,
                CURRENT_SCHEMA_VERSION,
                cache_key,
            )
            self._delete_cache_key(cache_key)
            return False

        return True

    def _delete_cache_key(self, cache_key: str) -> None:
        """删除指定缓存键

        Args:
            cache_key: 缓存键
        """
        try:
            self._db.conn.execute(
                "DELETE FROM reviews WHERE cache_key = ?", (cache_key,)
            )
            self._db.conn.commit()
        except Exception as e:
            logger.error("删除缓存失败: %s - %s", cache_key, e)

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
            data = normalize_review_payload(data)
            valid_fields = {f.name for f in fields(ReviewData)}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return ReviewData(**filtered)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("缓存数据反序列化失败: %s", e)
            return None

    @staticmethod
    def _extract_review_summary(review_json: str) -> dict:
        """Best-effort summary extraction for legacy cache rows."""
        try:
            data = json.loads(review_json)
            data = normalize_review_payload(data)
        except (json.JSONDecodeError, TypeError):
            return {}

        content = data.get("content") or data.get("summary") or ""
        if not content:
            parts = [
                data.get("background", ""),
                data.get("musicology", ""),
                data.get("why_listen", ""),
            ]
            content = " ".join(part for part in parts if isinstance(part, str))

        return {
            "rating": data.get("rating"),
            "emotion": data.get("emotion", ""),
            "excerpt": content[:120] if isinstance(content, str) else "",
        }
