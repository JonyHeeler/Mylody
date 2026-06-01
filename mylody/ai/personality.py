"""音乐人格生成：基于历史乐评与生成时间复用乐评 AI 接口"""

import logging

from mylody.ai.prompts.personality import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger("mylody.ai.personality")

PERSONALITY_TIMEOUT_SECONDS = 90
BLOCKED_TITLE_MARKERS = ("音乐人格年报", "私人音乐年报")


def strip_personality_title(content: str) -> str:
    """移除音乐人格正文开头的外层年报标题。"""
    lines = content.strip().splitlines()
    while lines and _is_blocked_title(lines[0]):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _is_blocked_title(line: str) -> bool:
    clean = line.strip().lstrip("#").strip()
    return any(marker in clean for marker in BLOCKED_TITLE_MARKERS)


async def generate_music_personality(ai_client, journey_items: list[dict]) -> str:
    """生成用户的音乐人格与音乐旅程回顾。

    Args:
        ai_client: 现有 AIClient 实例，复用乐评 API 配置和 Provider
        journey_items: 带生成时间的缓存乐评时间线

    Returns:
        str: 可直接展示给用户的音乐人格文本
    """
    prompt = build_user_prompt(journey_items)
    logger.info("生成音乐人格: %d 条乐评", len(journey_items))
    content = await ai_client.generate_text(
        SYSTEM_PROMPT,
        prompt,
        timeout_seconds=PERSONALITY_TIMEOUT_SECONDS,
    )
    return strip_personality_title(content)
