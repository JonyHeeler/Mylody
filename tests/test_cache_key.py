"""缓存 Key 标准化单元测试"""

import pytest

from mylody.cache.key import normalize_cache_key


def test_normal_key():
    """测试正常 key 生成"""
    result = normalize_cache_key("OneRepublic", "Counting Stars")
    assert result == "onerepublic::counting stars"


def test_case_normalization():
    """测试大小写标准化"""
    result = normalize_cache_key("ONEREPUBLIC", "COUNTING STARS")
    assert result == "onerepublic::counting stars"

    result = normalize_cache_key("onerepublic", "counting stars")
    assert result == "onerepublic::counting stars"


def test_empty_artist_fallback():
    """测试空 artist 降级"""
    result = normalize_cache_key("", "Counting Stars")
    assert result == "unknown::counting stars"

    result = normalize_cache_key("  ", "Counting Stars")
    assert result == "unknown::counting stars"


def test_trim_handling():
    """测试 trim 处理"""
    result = normalize_cache_key("  OneRepublic  ", "  Counting Stars  ")
    assert result == "onerepublic::counting stars"


def test_empty_both():
    """测试两者都为空"""
    result = normalize_cache_key("", "")
    assert result == "unknown::"


def test_none_values():
    """测试 None 值处理"""
    result = normalize_cache_key(None, "Test")
    assert result == "unknown::test"

    result = normalize_cache_key("Artist", None)
    assert result == "artist::"


def test_chinese_characters():
    """测试中文字符"""
    result = normalize_cache_key("周杰伦", "晴天")
    assert result == "周杰伦::晴天"


def test_mixed_whitespace():
    """测试混合空白字符"""
    result = normalize_cache_key("\t OneRepublic \n", "\t Counting Stars \n")
    assert result == "onerepublic::counting stars"
