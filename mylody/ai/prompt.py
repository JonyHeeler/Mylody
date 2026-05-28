"""Prompt 模板管理：构建 AI 乐评生成的系统和用户 Prompt"""

from mylody.types import MediaInfo

SYSTEM_PROMPT = """你是一位资深音乐评论家，拥有丰富的音乐理论知识和敏锐的审美品味。
请为用户正在收听的歌曲撰写专业、有深度的乐评。

你必须以严格的 JSON 格式回复，不要包含任何其他文字或 markdown 标记。
JSON 结构如下：
{
  "summary": "一句话概括这首歌（30字以内）",
  "emotion": "情感基调描述",
  "background": "创作背景或艺术家简介（100字以内）",
  "musicology": "音乐理论简析，如调性、节奏、编曲特点（100字以内）",
  "why_listen": "推荐理由（80字以内）",
  "similar_songs": ["相似歌曲1 - 艺术家", "相似歌曲2 - 艺术家"],
  "rating": 8.5
}
rating 为 0-10 的浮点数评分。similar_songs 推荐 3 首相似歌曲。"""

USER_TEMPLATE = "请为以下歌曲撰写乐评：\n歌名：{title}\n艺术家：{artist}\n专辑：{album}"


def build_user_prompt(track: MediaInfo) -> str:
    """根据媒体信息构建用户 Prompt

    Args:
        track: 当前播放曲目的媒体信息

    Returns:
        str: 格式化后的用户 Prompt 文本
    """
    return USER_TEMPLATE.format(
        title=track.title or "未知歌曲",
        artist=track.artist or "未知艺术家",
        album=track.album or "未知专辑",
    )
