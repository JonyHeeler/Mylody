"""Prompt 兼容门面：对外暴露乐评 Prompt 的旧导入路径"""

from mylody.ai.prompts.review import SYSTEM_PROMPT, build_user_prompt

__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
