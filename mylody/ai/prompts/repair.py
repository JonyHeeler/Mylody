"""乐评修复 Prompt 模板"""

REPAIR_PROMPT_SUFFIX = """

你上次返回的 JSON 未通过校验，请修正以下问题后重新返回：
{errors}

请确保返回符合要求的 JSON 格式。"""
