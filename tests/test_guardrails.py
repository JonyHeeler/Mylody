"""Guardrails 校验模块单元测试"""

import json

import pytest

from mylody.ai.guardrails import (
    ValidationResult,
    normalize_review_payload,
    validate_and_extract,
    validate_review,
)
from mylody.types import ReviewData


def _make_valid_data() -> dict:
    """创建有效的乐评数据"""
    return {
        "content": "一段优美的乐评",
        "emotion": "怀旧",
        "similar_songs": ["歌曲A - 艺术家A"],
        "rating": 8.0,
        "schema_version": "review_v2",
        "factuality_level": "metadata_only",
        "analysis_basis": "track_metadata",
        "known_facts": [],
        "uncertain_facts": [],
        "safety_notes": [],
    }


def test_validate_valid_data():
    """测试校验有效数据"""
    data = _make_valid_data()
    result = validate_review(data)

    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_not_dict():
    """测试非字典类型"""
    result = validate_review(["not", "a", "dict"])

    assert result.valid is False
    assert "不是字典类型" in result.errors[0]


def test_validate_missing_required_fields():
    """测试缺少必需字段"""
    data = {"content": "只有内容"}
    result = validate_review(data)

    assert result.valid is False
    assert any("emotion" in e for e in result.errors)
    assert any("similar_songs" in e for e in result.errors)
    assert any("rating" in e for e in result.errors)


def test_validate_invalid_rating_type():
    """测试 rating 类型错误"""
    data = _make_valid_data()
    data["rating"] = "not_a_number"
    result = validate_review(data)

    assert result.valid is False
    assert any("rating" in e and "数字" in e for e in result.errors)


def test_validate_rating_out_of_range():
    """测试 rating 超出范围"""
    data = _make_valid_data()
    data["rating"] = 11.0
    result = validate_review(data)

    assert result.valid is False
    assert any("0-10" in e for e in result.errors)


def test_validate_rating_negative():
    """测试负数 rating"""
    data = _make_valid_data()
    data["rating"] = -1.0
    result = validate_review(data)

    assert result.valid is False


def test_validate_wrong_schema_version():
    """测试错误的 schema_version 会被归一化"""
    data = _make_valid_data()
    data["schema_version"] = "review_v1"
    result = validate_review(data)

    assert result.valid is True
    assert normalize_review_payload(data)["schema_version"] == "review_v2"


def test_validate_invalid_factuality_level():
    """测试无效的 factuality_level（产生警告）"""
    data = _make_valid_data()
    data["factuality_level"] = "invalid_level"
    result = validate_review(data)

    assert result.valid is True
    assert len(result.warnings) > 0
    assert any("factuality_level" in w for w in result.warnings)


def test_validate_high_risk_content_without_evidence():
    """测试无证据时的高风险内容（应报错）"""
    data = _make_valid_data()
    data["content"] = "这首歌发行于2013年，制作人是Ryan Tedder"
    data["analysis_basis"] = "track_metadata"
    data["known_facts"] = []
    result = validate_review(data)

    assert result.valid is False
    assert any("高风险" in e for e in result.errors)


def test_validate_theme_claim_without_evidence():
    """测试无证据时的歌词主题断言（应报错）"""
    data = _make_valid_data()
    data["content"] = "这是一首情歌，歌词讲述了恋人之间的分手与复合。"
    data["analysis_basis"] = "track_metadata"
    data["known_facts"] = []
    result = validate_review(data)

    assert result.valid is False
    assert any("歌词主题断言" in e for e in result.errors)


def test_validate_high_risk_content_with_evidence():
    """测试有证据时允许高风险内容"""
    data = _make_valid_data()
    data["content"] = "这首歌发行于2013年，制作人是Ryan Tedder"
    data["analysis_basis"] = "external_evidence"
    data["known_facts"] = ["发行于2013年", "制作人是Ryan Tedder"]
    result = validate_review(data)

    assert result.valid is True
    assert len(result.warnings) == 0


def test_validate_and_extract_success():
    """测试校验并提取成功"""
    data = _make_valid_data()
    review = validate_and_extract(data)

    assert review is not None
    assert isinstance(review, ReviewData)
    assert review.content == "一段优美的乐评"
    assert review.schema_version == "review_v2"


def test_normalize_review_payload_merges_legacy_sections():
    """测试旧版分段输出会合并为完整乐评正文"""
    data = {
        "review": {
            "summary": "第一句摘要。",
            "background": "背景段落。",
            "musicology": "听感段落。",
            "emotion": "怀旧",
            "similar_songs": ["A - B"],
            "rating": 8.0,
        }
    }

    normalized = normalize_review_payload(data)

    assert normalized["content"] == "第一句摘要。\n\n背景段落。\n\n听感段落。"
    assert normalized["quote"] == "第一句摘要。"
    assert normalized["schema_version"] == "review_v2"


def test_normalize_review_payload_adds_quote_from_content():
    """测试缺少 quote 时从正文提取金句"""
    data = _make_valid_data()
    data.pop("quote", None)
    data["content"] = "像雨夜里的一盏灯，照见心里没有说完的话。后面还有更多内容。"

    normalized = normalize_review_payload(data)

    assert normalized["quote"] == "像雨夜里的一盏灯，照见心里没有说完的话。"


def test_validate_and_extract_failure():
    """测试校验失败返回 None"""
    data = {"content": "不完整"}
    review = validate_and_extract(data)

    assert review is None


def test_validate_and_extract_invalid_json():
    """测试无效数据返回 None"""
    review = validate_and_extract("not a dict")

    assert review is None


def test_high_risk_patterns():
    """测试各种高风险模式"""
    data = _make_valid_data()

    high_risk_texts = [
        "收录于专辑《Native》",
        "BPM为120",
        "采用大调调式",
        "采样了经典歌曲",
        "获得格莱美奖",
        "登上Billboard榜单",
        "和声进行非常复杂",
    ]

    for text in high_risk_texts:
        data["content"] = text
        data["analysis_basis"] = "track_metadata"
        data["known_facts"] = []
        result = validate_review(data)
        assert result.valid is False, f"应该检测到高风险并报错: {text}"
        assert any("高风险" in e for e in result.errors)
