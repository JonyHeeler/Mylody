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


def test_build_user_prompt_with_windows_metadata():
    """测试 Prompt 包含 Windows 提供的可选元数据"""
    track = MediaInfo(
        title="All We Are",
        artist="OneRepublic",
        album="Dreaming Out Loud",
        album_artist="OneRepublic",
        track_number=7,
        album_track_count=16,
        genres=["Pop", "Rock"],
        duration_ms=245000,
    )
    prompt = build_user_prompt(track)

    assert "专辑艺术家：OneRepublic" in prompt
    assert "曲目序号：7/16" in prompt
    assert "流派标签：Pop, Rock" in prompt
    assert "曲目时长：4:05" in prompt


def test_system_prompt_contains_json_structure():
    """测试系统 Prompt 包含 JSON 结构定义"""
    assert "quote" in SYSTEM_PROMPT
    assert "content" in SYSTEM_PROMPT
    assert "emotion" in SYSTEM_PROMPT
    assert "similar_songs" in SYSTEM_PROMPT
    assert "rating" in SYSTEM_PROMPT


def test_system_prompt_requires_json():
    """测试系统 Prompt 要求 JSON 格式输出"""
    assert "JSON" in SYSTEM_PROMPT


def test_system_prompt_contains_factuality_fields():
    """测试系统 Prompt 包含事实性字段定义"""
    assert "factuality_level" in SYSTEM_PROMPT
    assert "analysis_basis" in SYSTEM_PROMPT
    assert "known_facts" in SYSTEM_PROMPT
    assert "uncertain_facts" in SYSTEM_PROMPT


def test_system_prompt_contains_safety_rules():
    """测试系统 Prompt 包含安全规则"""
    assert "禁止编造" in SYSTEM_PROMPT
    assert "制作人" in SYSTEM_PROMPT
    assert "BPM" in SYSTEM_PROMPT
    assert "发行年份" in SYSTEM_PROMPT


def test_system_prompt_requests_longer_review():
    """测试系统 Prompt 要求更长乐评"""
    assert "900-1500" in SYSTEM_PROMPT
    assert "金句" in SYSTEM_PROMPT


def test_system_prompt_contains_story_review_style():
    """测试 System Prompt 包含故事化乐评风格"""
    assert "故事化中文乐评" in SYSTEM_PROMPT
    assert "声音 -> 情绪" in SYSTEM_PROMPT
    assert "普通音乐爱好者" in SYSTEM_PROMPT


def test_system_prompt_blocks_unsupported_theme_claims():
    """测试 System Prompt 禁止无证据歌词主题判断"""
    assert "无证据断言歌词主题" in SYSTEM_PROMPT
    assert "这是情歌" in SYSTEM_PROMPT
    assert "写给前任" in SYSTEM_PROMPT


def test_build_user_prompt_with_musicbrainz_evidence():
    """测试 MusicBrainz evidence 会进入 Prompt"""
    track = MediaInfo(title="Counting Stars", artist="OneRepublic", album="Native")
    evidence = {
        "known_facts": ["发行于2013年", "收录于专辑《Native》"],
        "uncertain_facts": ["可能在伦敦录制"],
    }
    prompt = build_user_prompt(track, evidence)

    assert "已确认事实" in prompt
    assert "发行于2013年" in prompt
    assert "未确认信息" in prompt
    assert "可能在伦敦录制" in prompt
    assert "Counting Stars" in prompt


def test_build_user_prompt_with_wikipedia_evidence():
    """测试 Wikipedia evidence 会进入 Prompt"""
    track = MediaInfo(title="Nude", artist="Radiohead", album="In Rainbows")
    evidence = {
        "known_facts": [
            "[wikipedia] artist_background: Radiohead are an English rock band.",
        ],
        "uncertain_facts": [],
    }
    prompt = build_user_prompt(track, evidence)

    assert "外部已确认事实" in prompt
    assert "Radiohead are an English rock band" in prompt


def test_build_user_prompt_with_empty_legacy_evidence():
    """测试空旧 evidence 参数不会追加证据区块"""
    track = MediaInfo(title="Test", artist="Test")
    evidence = {"known_facts": [], "uncertain_facts": []}
    prompt = build_user_prompt(track, evidence)

    assert "已确认事实" not in prompt
    assert "Test" in prompt


def test_build_user_prompt_without_evidence():
    """测试无证据时的 Prompt 构建（向后兼容）"""
    track = MediaInfo(title="Test", artist="Test")
    prompt = build_user_prompt(track)

    assert "已确认事实" not in prompt
    assert "Test" in prompt


def test_system_prompt_excludes_web_search_rules():
    """测试系统 Prompt 不再包含联网搜索规则"""
    assert "联网搜索结果" not in SYSTEM_PROMPT
    assert "搜索结果仅供参考" not in SYSTEM_PROMPT
    assert "据媒体报道" not in SYSTEM_PROMPT
