"""AI Client 单元测试"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mylody.ai.client import AIClient
from mylody.types import MediaInfo, ReviewData


def _make_config(api_key: str = "test-key") -> MagicMock:
    """创建模拟配置对象"""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "ai.api_key": api_key,
        "ai.model": "deepseek-chat",
        "ai.base_url": "https://api.deepseek.com",
        "ai.timeout_seconds": 30,
    }.get(key, default)
    return config


VALID_RESPONSE = json.dumps({
    "content": "Counting Stars 像一通深夜电话，在焦虑和希望之间摇摆。OneRepublic 用明快的节奏和朗朗上口的旋律，把对金钱与信仰的反思包装成了一首让人忍不住跟着点头的流行摇滚。",
    "emotion": "积极向上",
    "similar_songs": ["Apologize - OneRepublic"],
    "rating": 8.5,
    "schema_version": "review_v2",
    "factuality_level": "metadata_only",
    "analysis_basis": "track_metadata",
    "known_facts": [],
    "uncertain_facts": [],
    "safety_notes": [],
})


@pytest.fixture
def mock_provider():
    """创建模拟 Provider"""
    provider = AsyncMock()
    provider.chat.return_value = VALID_RESPONSE
    return provider


@pytest.mark.asyncio
async def test_generate_review_success(mock_provider):
    """测试成功生成乐评"""
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Counting Stars", artist="OneRepublic")
        result = await client.generate_review(track)

    assert result is not None
    assert isinstance(result, ReviewData)
    assert "Counting Stars" in result.content
    assert result.rating == 8.5
    assert len(result.similar_songs) == 1


@pytest.mark.asyncio
async def test_generate_review_invalid_json(mock_provider):
    """测试 AI 返回非 JSON 格式"""
    mock_provider.chat.return_value = "这不是一个 JSON 字符串"
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is None


@pytest.mark.asyncio
async def test_generate_review_json_not_dict(mock_provider):
    """测试 AI 返回非字典类型的 JSON"""
    mock_provider.chat.return_value = json.dumps(["not", "a", "dict"])
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is None


@pytest.mark.asyncio
async def test_generate_review_provider_exception(mock_provider):
    """测试 Provider 抛出异常"""
    mock_provider.chat.side_effect = ConnectionError("网络连接失败")
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is None


@pytest.mark.asyncio
async def test_generate_review_timeout(mock_provider):
    """测试请求超时"""
    mock_provider.chat.side_effect = TimeoutError("请求超时")
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is None


@pytest.mark.asyncio
async def test_generate_review_partial_fields(mock_provider):
    """测试 AI 返回部分字段（缺少 schema_version 会校验失败）"""
    partial = json.dumps({"content": "一段简短的乐评", "rating": 7.0})
    mock_provider.chat.return_value = partial
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is None


@pytest.mark.asyncio
async def test_generate_review_extra_fields_ignored(mock_provider):
    """测试 AI 返回额外字段被忽略"""
    extra = json.dumps({
        "content": "测试乐评",
        "emotion": "平静",
        "similar_songs": ["歌曲A - 艺术家A"],
        "rating": 5.0,
        "schema_version": "review_v2",
        "unknown_field": "应被忽略",
        "another_extra": 123,
    })
    mock_provider.chat.return_value = extra
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is not None
    assert result.content == "测试乐评"


def test_create_provider_openai_compatible():
    """测试创建 OpenAI-compatible Provider"""
    config = _make_config()

    with patch("mylody.ai.provider_openai.OpenAIProvider") as MockProvider:
        MockProvider.return_value = MagicMock()
        AIClient(config)
        MockProvider.assert_called_once()
        call_args = MockProvider.call_args
        assert call_args[1]["base_url"] == "https://api.deepseek.com"
        assert call_args[1]["model"] == "deepseek-chat"


def test_create_provider_openai_without_base_url():
    """测试 OpenAI Provider 缺少 base_url 时报错"""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "ai.api_key": "test-key",
        "ai.model": "deepseek-chat",
        "ai.base_url": "",
        "ai.timeout_seconds": 30,
    }.get(key, default)

    with pytest.raises(ValueError, match="必须配置 ai.base_url"):
        AIClient(config)


def test_parse_json_from_markdown_fence(mock_provider):
    """测试能从 markdown 代码块中提取 JSON"""
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        result = client._parse_and_validate(f"```json\n{VALID_RESPONSE}\n```")

    assert result is not None
    assert result.rating == 8.5


@pytest.mark.asyncio
async def test_generate_review_ignores_legacy_evidence_argument(mock_provider):
    """测试旧 evidence 参数不会触发额外联网参数"""
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Counting Stars", artist="OneRepublic")
        evidence_bundle = {
            "known_facts": ["发行于2013年"],
            "uncertain_facts": [],
            "confidence": 0.9,
        }
        result = await client.generate_review(track, evidence_bundle=evidence_bundle)

    assert result is not None
    mock_provider.chat.assert_called_once()
    assert mock_provider.chat.call_args.kwargs == {}
