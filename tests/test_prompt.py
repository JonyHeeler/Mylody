"""Prompt 模板单元测试"""

from mylody.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from mylody.types import MediaInfo


def test_build_user_prompt_normal():
    """测试正常歌曲信息的 Prompt 构建"""
    track = MediaInfo(title="Counting Stars", artist="OneRepublic", album="Native")
    prompt = build_user_prompt(track)

    assert "Counting Stars" in prompt
    assert "OneRepublic" in prompt
    assert "Native" in prompt


def test_build_user_prompt_missing_fields():
    """测试缺失字段时使用默认值"""
    track = MediaInfo()
    prompt = build_user_prompt(track)

    assert "未知歌曲" in prompt
    assert "未知艺术家" in prompt
    assert "未知专辑" in prompt


def test_build_user_prompt_partial_fields():
    """测试部分字段缺失的情况"""
    track = MediaInfo(title="Hello", artist="Adele")
    prompt = build_user_prompt(track)

    assert "Hello" in prompt
    assert "Adele" in prompt
    assert "未知专辑" in prompt


def test_system_prompt_contains_json_structure():
    """测试系统 Prompt 包含 JSON 结构定义"""
    assert "summary" in SYSTEM_PROMPT
    assert "emotion" in SYSTEM_PROMPT
    assert "background" in SYSTEM_PROMPT
    assert "musicology" in SYSTEM_PROMPT
    assert "why_listen" in SYSTEM_PROMPT
    assert "similar_songs" in SYSTEM_PROMPT
    assert "rating" in SYSTEM_PROMPT


def test_system_prompt_requires_json():
    """测试系统 Prompt 要求 JSON 格式输出"""
    assert "JSON" in SYSTEM_PROMPT
