"""SQLite 数据库连接管理：表创建、异常恢复"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("mylody.cache.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key   TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    artist      TEXT,
    album       TEXT,
    review_json TEXT NOT NULL,
    ai_model    TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_reviews_cache_key ON reviews (cache_key);
"""


class Database:
    """SQLite 数据库连接管理器

    负责连接管理、表创建和数据库损坏时的自动恢复。

    Args:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """建立数据库连接，确保目录和表存在"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._ensure_table()
            logger.info("数据库连接成功: %s", self._db_path)
        except sqlite3.DatabaseError:
            logger.warning("数据库损坏，正在恢复: %s", self._db_path)
            self._recover_from_corruption()

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        """获取当前数据库连接

        Returns:
            sqlite3.Connection: 数据库连接对象

        Raises:
            RuntimeError: 数据库未连接时抛出
        """
        if self._conn is None:
            raise RuntimeError("数据库未连接，请先调用 connect()")
        return self._conn

    def _ensure_table(self) -> None:
        """确保 reviews 表和索引存在"""
        self.conn.executescript(CREATE_TABLE_SQL + CREATE_INDEX_SQL)

    def _recover_from_corruption(self) -> None:
        """数据库损坏时备份旧文件并重建空数据库"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

        if self._db_path.exists():
            backup_name = f"{self._db_path.stem}_corrupted_{datetime.now():%Y%m%d%H%M%S}{self._db_path.suffix}"
            backup_path = self._db_path.parent / backup_name
            shutil.move(str(self._db_path), str(backup_path))
            logger.info("已备份损坏数据库: %s", backup_path)

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_table()
        logger.info("数据库重建完成: %s", self._db_path)
