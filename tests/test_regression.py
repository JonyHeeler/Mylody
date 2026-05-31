"""回归测试：端到端流程验证"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mylody.ai.client import AIClient
from mylody.ai.guardrails import validate_and_extract, validate_review
from mylody.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from mylody.evidence.service import EvidenceService
from mylody.evidence.types import (
    ArtistInfo,
    EvidenceBundle,
    GenreTag,
    MusicMetadata,
    MusicSearchResult,
    ReleaseInfo,
)
from mylody.types import MediaInfo, ReviewData

from .regression_test_cases import QUALITY_METRICS, TEST_CASES


def _make_config() -> MagicMock:
    """创建模拟配置"""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "ai.api_key": "test-key",
        "ai.model": "deepseek-chat",
        "ai.base_url": "https://api.deepseek.com",
        "ai.timeout_seconds": 30,
    }.get(key, default)
    return config


def _make_valid_review_data() -> dict:
    """创建有效的乐评数据"""
    return {
        "content": "这是一首测试歌曲的乐评内容。" * 50,
        "emotion": "怀旧",
        "similar_songs": ["歌曲A - 艺术家A", "歌曲B - 艺术家B", "歌曲C - 艺术家C"],
        "rating": 8.5,
        "schema_version": "review_v2",
        "factuality_level": "metadata_only",
        "analysis_basis": "track_metadata",
        "known_facts": [],
        "uncertain_facts": [],
        "safety_notes": [],
    }


def _make_metadata(title: str, artist: str) -> MusicMetadata:
    """创建测试用 MusicMetadata"""
    return MusicMetadata(
        recording_mbid="test-mbid-123",
        title=title,
        length_ms=240000,
        artists=[ArtistInfo(mbid="artist-mbid", name=artist)],
        releases=[
            ReleaseInfo(
                mbid="release-mbid",
                title="Test Album",
                date="2020-01-01",
                country="US",
                label_names=["Test Label"],
            )
        ],
        isrcs=["TEST12345678"],
        genres=[GenreTag(name="pop", count=100)],
        tags=[GenreTag(name="test", count=50)],
    )


class TestEvidenceBuilding:
    """测试证据构建"""

    def test_build_evidence_with_metadata(self):
        """测试有元数据时的证据构建"""
        service = EvidenceService()
        metadata = _make_metadata("Test Song", "Test Artist")

        bundle = service.build_evidence("Test Song", "Test Artist", "Test Album", metadata)

        assert bundle.track_title == "Test Song"
        assert bundle.artist == "Test Artist"
        assert bundle.canonical_id == "test-mbid-123"
        assert bundle.confidence > 0
        assert len(bundle.known_facts) > 0
        assert len(bundle.sources) > 0

    def test_build_evidence_without_metadata(self):
        """测试无元数据时的证据构建"""
        service = EvidenceService()

        bundle = service.build_evidence("Test", "Test", "Test", None)

        assert bundle.confidence == 0.0
        assert len(bundle.known_facts) == 0
        assert len(bundle.sources) == 0

    def test_evidence_contains_artists(self):
        """测试证据包含艺术家信息"""
        service = EvidenceService()
        metadata = _make_metadata("Test", "Radiohead")

        bundle = service.build_evidence("Test", "Radiohead", "", metadata)

        artist_facts = [f for f in bundle.known_facts if f.key == "artists"]
        assert len(artist_facts) == 1
        assert "Radiohead" in artist_facts[0].value

    def test_evidence_contains_isrcs(self):
        """测试证据包含 ISRC"""
        service = EvidenceService()
        metadata = _make_metadata("Test", "Test")

        bundle = service.build_evidence("Test", "Test", "", metadata)

        isrc_facts = [f for f in bundle.known_facts if f.key == "isrcs"]
        assert len(isrc_facts) == 1
        assert "TEST12345678" in isrc_facts[0].value


class TestGuardrails:
    """测试 Guardrails 校验"""

    def test_valid_data_passes(self):
        """测试有效数据通过校验"""
        data = _make_valid_review_data()
        result = validate_review(data)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_schema_version_is_normalized(self):
        """测试缺少 schema_version 时自动归一化"""
        data = _make_valid_review_data()
        del data["schema_version"]
        result = validate_review(data)

        assert result.valid is True
        review = validate_and_extract(data)
        assert review is not None
        assert review.schema_version == "review_v2"

    def test_invalid_rating_fails(self):
        """测试无效 rating 失败"""
        data = _make_valid_review_data()
        data["rating"] = 11.0
        result = validate_review(data)

        assert result.valid is False

    def test_high_risk_content_without_evidence(self):
        """测试无证据时的高风险内容（应报错）"""
        data = _make_valid_review_data()
        data["content"] = "这首歌发行于2013年，制作人是Ryan Tedder"
        data["analysis_basis"] = "track_metadata"
        data["known_facts"] = []
        result = validate_review(data)

        assert result.valid is False
        assert any("高风险" in e for e in result.errors)

    def test_validate_and_extract_success(self):
        """测试校验并提取成功"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        assert isinstance(review, ReviewData)
        assert review.schema_version == "review_v2"


class TestPromptBuilding:
    """测试 Prompt 构建"""

    def test_prompt_with_musicbrainz_evidence(self):
        """测试 MusicBrainz 证据进入 Prompt"""
        track = MediaInfo(title="Test", artist="Test", album="Test")
        evidence = {
            "known_facts": ["发行于2020年", "流派: pop"],
            "uncertain_facts": ["可能在洛杉矶录制"],
        }

        prompt = build_user_prompt(track, evidence)

        assert "已确认事实" in prompt
        assert "发行于2020年" in prompt
        assert "Test" in prompt

    def test_prompt_without_evidence(self):
        """测试无证据的 Prompt"""
        track = MediaInfo(title="Test", artist="Test")

        prompt = build_user_prompt(track)

        assert "已确认事实" not in prompt
        assert "Test" in prompt

    def test_system_prompt_contains_safety_rules(self):
        """测试系统 Prompt 包含安全规则"""
        assert "禁止编造" in SYSTEM_PROMPT
        assert "制作人" in SYSTEM_PROMPT
        assert "BPM" in SYSTEM_PROMPT

    def test_system_prompt_excludes_web_search_rules(self):
        """测试系统 Prompt 不包含联网搜索规则"""
        assert "联网搜索结果" not in SYSTEM_PROMPT
        assert "搜索结果仅供参考" not in SYSTEM_PROMPT


class TestReviewDataStructure:
    """测试 ReviewData 结构"""

    def test_review_data_has_all_fields(self):
        """测试 ReviewData 包含所有必需字段"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        assert review.content != ""
        assert review.emotion != ""
        assert isinstance(review.similar_songs, list)
        assert 0 <= review.rating <= 10
        assert review.schema_version == "review_v2"
        assert review.factuality_level in ["metadata_only", "grounded", "mixed"]
        assert review.analysis_basis in ["track_metadata", "provided_context", "external_evidence"]
        assert isinstance(review.known_facts, list)
        assert isinstance(review.uncertain_facts, list)
        assert isinstance(review.safety_notes, list)

    def test_review_data_to_dict(self):
        """测试 ReviewData 转换为字典"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        d = review.to_dict()

        assert "content" in d
        assert "emotion" in d
        assert "similar_songs" in d
        assert "rating" in d
        assert "schema_version" in d
        assert "factuality_level" in d
        assert "known_facts" in d


class TestQualityMetrics:
    """测试质量指标"""

    def test_content_length_in_range(self):
        """测试内容长度在合理范围内"""
        data = _make_valid_review_data()
        data["content"] = "A" * 500
        review = validate_and_extract(data)

        assert review is not None
        assert QUALITY_METRICS["min_content_length"] <= len(review.content) <= QUALITY_METRICS["max_content_length"]

    def test_required_fields_present(self):
        """测试必需字段存在"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        for field in QUALITY_METRICS["required_fields"]:
            assert hasattr(review, field), f"缺少字段: {field}"

    def test_factuality_level_valid(self):
        """测试 factuality_level 有效"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        assert review.factuality_level in QUALITY_METRICS["valid_factuality_levels"]

    def test_analysis_basis_valid(self):
        """测试 analysis_basis 有效"""
        data = _make_valid_review_data()
        review = validate_and_extract(data)

        assert review is not None
        assert review.analysis_basis in QUALITY_METRICS["valid_analysis_basis"]
