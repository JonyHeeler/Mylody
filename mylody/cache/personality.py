"""音乐人格本地缓存读写。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

BLOCKED_TITLE_MARKERS = ("音乐人格年报", "私人音乐年报")


class PersonalityCache:
    """Store and retrieve generated music personality snapshots."""

    def __init__(self, cache_manager) -> None:
        self._cache_manager = cache_manager

    def latest(self) -> Optional[dict]:
        """Return the latest saved personality snapshot."""
        row = self._cache_manager._db.conn.execute(
            """SELECT id, content, item_count, ai_model, created_at
               FROM personalities
               ORDER BY created_at DESC, id DESC
               LIMIT 1"""
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list(self, limit: int = 100) -> list[dict]:
        """Return saved personality snapshots, newest first."""
        rows = self._cache_manager._db.conn.execute(
            """SELECT id, content, item_count, ai_model, created_at
               FROM personalities
               ORDER BY created_at DESC, id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [self._row_to_dict(row, include_content=False) for row in rows]

    def get(self, personality_id: int) -> Optional[dict]:
        """Return one saved personality snapshot by id."""
        row = self._cache_manager._db.conn.execute(
            """SELECT id, content, item_count, ai_model, created_at
               FROM personalities
               WHERE id = ?""",
            (personality_id,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def save(self, content: str, item_count: int, model: str = "") -> dict:
        """Save a generated personality snapshot."""
        created_at = datetime.utcnow().isoformat()
        cursor = self._cache_manager._db.conn.execute(
            """INSERT INTO personalities (content, item_count, ai_model, created_at)
               VALUES (?, ?, ?, ?)""",
            (content, item_count, model, created_at),
        )
        self._cache_manager._db.conn.commit()
        return {
            "id": cursor.lastrowid,
            "content": content,
            "item_count": item_count,
            "model": model,
            "created_at": created_at,
        }

    @staticmethod
    def _row_to_dict(row, include_content: bool = True) -> dict:
        personality_id, content, item_count, model, created_at = row
        content = _strip_outer_title(content)
        item = {
            "id": personality_id,
            "item_count": item_count,
            "model": model or "",
            "created_at": created_at,
            "excerpt": content[:160],
        }
        if include_content:
            item["content"] = content
        return item


def _strip_outer_title(content: str) -> str:
    lines = content.strip().splitlines()
    while lines and _is_blocked_title(lines[0]):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _is_blocked_title(line: str) -> bool:
    clean = line.strip().lstrip("#").strip()
    return any(marker in clean for marker in BLOCKED_TITLE_MARKERS)
