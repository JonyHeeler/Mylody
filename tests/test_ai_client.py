"""AI Client 单元测试"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mylody.ai.client import AIClient
from mylody.types import MediaInfo, ReviewData


def _make_config(provider: str = "anthropic", api_key: str = "test-key") -> MagicMock:
    """创建模拟配置对象"""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "ai.provider": provider,
        "ai.api_key": api_key,
        "ai.model": "test-model",
        "ai.base_url": "",
        "ai.timeout_seconds": 15,
    }.get(key, default)
    return config


VALID_RESPONSE = json.dumps({
    "summary": "一首充满活力的流行摇滚",
    "emotion": "积极向上",
    "background": "OneRepublic 美国流行摇滚乐队",
    "musicology": "4/4拍，大调，节奏明快",
    "why_listen": "旋律朗朗上口，歌词励志",
    "similar_songs": ["Apologize - OneRepublic"],
    "rating": 8.5,
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
    assert result.summary == "一首充满活力的流行摇滚"
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
    """测试 AI 返回部分字段"""
    partial = json.dumps({"summary": "测试概括", "rating": 7.0})
    mock_provider.chat.return_value = partial
    config = _make_config()

    with patch("mylody.ai.client.AIClient._create_provider", return_value=mock_provider):
        client = AIClient(config)
        track = MediaInfo(title="Test", artist="Test")
        result = await client.generate_review(track)

    assert result is not None
    assert result.summary == "测试概括"
    assert result.rating == 7.0
    assert result.emotion == ""


@pytest.mark.asyncio
async def test_generate_review_extra_fields_ignored(mock_provider):
    """测试 AI 返回额外字段被忽略"""
    extra = json.dumps({
        "summary": "测试",
        "rating": 5.0,
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
    assert result.summary == "测试"


def test_create_provider_anthropic():
    """测试创建 Anthropic Provider"""
    config = _make_config(provider="anthropic")

    with patch("mylody.ai.provider_anthropic.AnthropicProvider") as MockProvider:
        MockProvider.return_value = MagicMock()
        AIClient(config)
        MockProvider.assert_called_once()


def test_create_provider_openai():
    """测试创建 OpenAI Provider"""
    config = _make_config(provider="openai")

    with patch("mylody.ai.provider_openai.OpenAIProvider") as MockProvider:
        MockProvider.return_value = MagicMock()
        AIClient(config)
        MockProvider.assert_called_once()
