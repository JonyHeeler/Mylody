"""缓存管理器单元测试"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mylody.cache.db import Database
from mylody.cache.manager import CacheManager
from mylody.types import ReviewData


@pytest.fixture
def tmp_db_path(tmp_path):
    """提供临时数据库路径"""
    return str(tmp_path / "test_reviews.db")


@pytest.fixture
def cache_manager(tmp_db_path):
    """创建临时缓存管理器"""
    manager = CacheManager(db_path=tmp_db_path, cache_ttl_days=0)
    yield manager
    manager.close()


@pytest.fixture
def sample_review():
    """创建示例乐评数据"""
    return ReviewData(
        content="Counting Stars 像一通深夜电话，在焦虑和希望之间摇摆。",
        emotion="积极向上",
        similar_songs=["Apologize - OneRepublic"],
        rating=8.5,
    )


def test_put_and_get_basic(cache_manager, sample_review):
    """测试基本的缓存写入和读取"""
    result = cache_manager.put(
        "OneRepublic", "Counting Stars", "Native", sample_review, model="test-model"
    )
    assert result is True

    cached = cache_manager.get("OneRepublic", "Counting Stars")
    assert cached is not None
    assert cached.content == sample_review.content
    assert cached.rating == sample_review.rating
    assert cached.similar_songs == sample_review.similar_songs


def test_cache_hit_no_ai_call(cache_manager, sample_review):
    """测试缓存命中（第二次读取直接返回缓存）"""
    cache_manager.put("OneRepublic", "Counting Stars", "Native", sample_review)

    first = cache_manager.get("OneRepublic", "Counting Stars")
    second = cache_manager.get("OneRepublic", "Counting Stars")

    assert first is not None
    assert second is not None
    assert first.content == second.content


def test_cache_miss(cache_manager):
    """测试缓存未命中"""
    result = cache_manager.get("Unknown Artist", "Unknown Song")
    assert result is None


def test_cache_overwrite(cache_manager, sample_review):
    """测试缓存覆盖写入"""
    cache_manager.put("Artist", "Title", "Album", sample_review)

    updated = ReviewData(content="更新后的乐评", rating=9.0)
    cache_manager.put("Artist", "Title", "Album", updated)

    cached = cache_manager.get("Artist", "Title")
    assert cached is not None
    assert cached.content == "更新后的乐评"
    assert cached.rating == 9.0


def test_delete_cache(cache_manager, sample_review):
    """测试删除缓存"""
    cache_manager.put("OneRepublic", "Counting Stars", "Native", sample_review)

    result = cache_manager.delete("OneRepublic", "Counting Stars")
    assert result is True

    cached = cache_manager.get("OneRepublic", "Counting Stars")
    assert cached is None


def test_delete_nonexistent(cache_manager):
    """测试删除不存在的缓存"""
    result = cache_manager.delete("Unknown", "Unknown")
    assert result is False


def test_stats(cache_manager, sample_review):
    """测试缓存统计"""
    stats = cache_manager.stats()
    assert stats["total"] == 0

    cache_manager.put("Artist1", "Title1", "Album1", sample_review)
    cache_manager.put("Artist2", "Title2", "Album2", sample_review)

    stats = cache_manager.stats()
    assert stats["total"] == 2
    assert stats["ttl_days"] == 0


def test_cache_expired(tmp_path):
    """测试缓存过期"""
    db_path = str(tmp_path / "expired_test.db")
    manager = CacheManager(db_path=db_path, cache_ttl_days=1)

    review = ReviewData(content="测试乐评", rating=5.0)
    manager.put("Artist", "Title", "Album", review)

    manager._db.conn.execute(
        "UPDATE reviews SET updated_at = ? WHERE cache_key = ?",
        ((datetime.utcnow() - timedelta(days=2)).isoformat(), "artist::title"),
    )
    manager._db.conn.commit()

    cached = manager.get("Artist", "Title")
    assert cached is None

    manager.close()


def test_cache_no_expire_with_ttl_zero(tmp_path):
    """测试 TTL 为 0 时永不过期"""
    db_path = str(tmp_path / "no_expire_test.db")
    manager = CacheManager(db_path=db_path, cache_ttl_days=0)

    review = ReviewData(content="永不过期的乐评", rating=5.0)
    manager.put("Artist", "Title", "Album", review)

    manager._db.conn.execute(
        "UPDATE reviews SET updated_at = ? WHERE cache_key = ?",
        ((datetime.utcnow() - timedelta(days=365)).isoformat(), "artist::title"),
    )
    manager._db.conn.commit()

    cached = manager.get("Artist", "Title")
    assert cached is not None
    assert cached.content == "永不过期的乐评"

    manager.close()


def test_database_corruption_recovery(tmp_path):
    """测试数据库损坏恢复"""
    db_path = tmp_path / "corrupt_test.db"
    db_path.write_bytes(b"this is not a valid sqlite database")

    manager = CacheManager(db_path=str(db_path), cache_ttl_days=0)

    review = ReviewData(content="恢复后写入", rating=5.0)
    result = manager.put("Artist", "Title", "Album", review)
    assert result is True

    cached = manager.get("Artist", "Title")
    assert cached is not None
    assert cached.content == "恢复后写入"

    backup_files = list(tmp_path.glob("corrupt_test_corrupted_*.db"))
    assert len(backup_files) == 1

    manager.close()


def test_case_insensitive_key(cache_manager, sample_review):
    """测试大小写不敏感的缓存 Key"""
    cache_manager.put("ONEREPUBLIC", "COUNTING STARS", "Native", sample_review)

    cached = cache_manager.get("onerepublic", "counting stars")
    assert cached is not None
    assert cached.content == sample_review.content


def test_deserialize_review(cache_manager, sample_review):
    """测试乐评反序列化完整性"""
    cache_manager.put("Artist", "Title", "Album", sample_review, model="test-model")

    cached = cache_manager.get("Artist", "Title")
    assert cached is not None
    assert cached.content == sample_review.content
    assert cached.emotion == sample_review.emotion
    assert cached.similar_songs == sample_review.similar_songs
    assert cached.rating == sample_review.rating


def test_schema_version_mismatch(tmp_path):
    """测试 schema 版本不匹配时可兼容读取"""
    db_path = str(tmp_path / "schema_test.db")
    manager = CacheManager(db_path=db_path, cache_ttl_days=0)

    review = ReviewData(content="旧版本乐评", rating=5.0)
    manager.put("Artist", "Title", "Album", review)

    manager._db.conn.execute(
        """UPDATE reviews SET review_json = ? WHERE cache_key = ?""",
        (json.dumps({
            "content": "旧版本乐评",
            "rating": 5.0,
            "schema_version": "review_v1",
        }), "artist::title"),
    )
    manager._db.conn.commit()

    cached = manager.get("Artist", "Title")
    assert cached is not None
    assert cached.schema_version == "review_v2"

    manager.close()


def test_schema_version_missing(tmp_path):
    """测试缺少 schema_version 时可兼容读取"""
    db_path = str(tmp_path / "no_version_test.db")
    manager = CacheManager(db_path=db_path, cache_ttl_days=0)

    review = ReviewData(content="无版本乐评", rating=5.0)
    manager.put("Artist", "Title", "Album", review)

    manager._db.conn.execute(
        """UPDATE reviews SET review_json = ? WHERE cache_key = ?""",
        (json.dumps({
            "content": "无版本乐评",
            "rating": 5.0,
        }), "artist::title"),
    )
    manager._db.conn.commit()

    cached = manager.get("Artist", "Title")
    assert cached is not None
    assert cached.schema_version == "review_v2"

    manager.close()


def test_schema_version_match(cache_manager, sample_review):
    """测试 schema 版本匹配时正常返回"""
    cache_manager.put("Artist", "Title", "Album", sample_review)

    cached = cache_manager.get("Artist", "Title")
    assert cached is not None
    assert cached.schema_version == "review_v2"
