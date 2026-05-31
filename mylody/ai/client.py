"""AI 乐评客户端：组装 Prompt → 调用 Provider → 解析 JSON → 校验 → 返回 ReviewData"""

import json
import asyncio
import logging
import re
from typing import Optional

from mylody.ai.guardrails import validate_and_extract, validate_review
from mylody.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from mylody.ai.provider_base import BaseProvider
from mylody.config import Config
from mylody.types import MediaInfo, ReviewData

logger = logging.getLogger("mylody.ai.client")

ERROR_MESSAGES = {
    401: "API Key 无效，请检查配置文件中的 ai.api_key",
    429: "API 请求频率超限，请稍后重试",
    500: "AI 服务不可用，请稍后重试",
}

REPAIR_PROMPT_SUFFIX = """

你上次返回的 JSON 未通过校验，请修正以下问题后重新返回：
{errors}

请确保返回符合要求的 JSON 格式。"""


class AIClient:
    """AI 乐评生成客户端

    负责组装 Prompt、调用 AI Provider、解析 JSON 响应、校验并返回结构化乐评。
    Args:
        config: Mylody 配置对象
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._timeout = config.get("ai.timeout_seconds", 30)
        self._provider = self._create_provider()

    def _create_provider(self) -> BaseProvider:
        """根据配置创建对应的 AI Provider

        Returns:
            BaseProvider: AI Provider 实例
        """
        api_key = self._config.get("ai.api_key", "")
        model = self._config.get("ai.model", "")
        base_url = self._config.get("ai.base_url", "")
        timeout = self._config.get("ai.timeout_seconds", 30)

        from mylody.ai.provider_openai import OpenAIProvider

        if not base_url:
            raise ValueError("必须配置 ai.base_url，例如 https://api.deepseek.com")

        return OpenAIProvider(
            api_key=api_key,
            model=model or "deepseek-chat",
            base_url=base_url,
            timeout=timeout,
        )

    async def generate_review(
        self,
        track: MediaInfo,
        evidence_bundle: Optional[dict] = None,
    ) -> Optional[ReviewData]:
        """为指定歌曲生成乐评

        Args:
            track: 歌曲媒体信息
            evidence_bundle: 保留兼容参数；普通 AI 模式不会主动联网获取证据

        Returns:
            Optional[ReviewData]: 乐评数据，失败时返回 None
        """
        user_prompt = build_user_prompt(track, evidence_bundle)

        logger.info(
            "生成乐评: %s - %s",
            track.artist,
            track.title,
        )

        try:
            raw = await self._call_provider(SYSTEM_PROMPT, user_prompt)
        except TimeoutError:
            logger.error("AI 请求超时")
            return None
        except Exception as e:
            self._handle_api_error(e)
            return None

        result = self._parse_and_validate(raw)

        if result is None:
            result = await self._retry_repair(SYSTEM_PROMPT, user_prompt, raw)

        return result

    async def _call_provider(self, system_prompt: str, user_prompt: str) -> str:
        """调用 OpenAI-compatible Provider"""
        return await asyncio.wait_for(
            self._provider.chat(system_prompt, user_prompt),
            timeout=self._timeout,
        )

    async def _retry_repair(
        self, system_prompt: str, user_prompt: str, raw: str
    ) -> Optional[ReviewData]:
        """重试修复校验失败的响应

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            raw: 上次 AI 返回的原始文本

        Returns:
            Optional[ReviewData]: 修复后的乐评数据，失败返回 None
        """
        data = self._load_json_response(raw)
        if data is None:
            return None

        result = validate_review(data)
        errors_text = "\n".join(f"- {e}" for e in result.errors)

        repair_prompt = user_prompt + REPAIR_PROMPT_SUFFIX.format(errors=errors_text)
        logger.info("尝试修复乐评输出")

        try:
            raw = await self._provider.chat(system_prompt, repair_prompt)
        except Exception as e:
            logger.error("修复请求失败: %s", e)
            return None

        return self._parse_and_validate(raw)

    def _parse_and_validate(self, raw: str) -> Optional[ReviewData]:
        """解析并校验 AI 返回的 JSON 响应

        Args:
            raw: AI 返回的原始文本

        Returns:
            Optional[ReviewData]: 校验通过返回 ReviewData，失败返回 None
        """
        data = self._load_json_response(raw)
        if data is None:
            logger.error("AI 返回非 JSON 格式: %s", raw[:200])
            return None

        if not isinstance(data, dict):
            logger.error("AI 返回非字典类型: %s", type(data).__name__)
            return None

        return validate_and_extract(data)

    @staticmethod
    def _load_json_response(raw: str) -> Optional[dict]:
        """从模型响应中解析 JSON，兼容代码块和前后说明文字"""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        text = raw.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    def _handle_api_error(self, error: Exception) -> None:
        """处理 API 错误并记录日志

        Args:
            error: 捕获的异常
        """
        error_type = type(error).__name__

        for code, message in ERROR_MESSAGES.items():
            if str(code) in str(error):
                logger.error("[%s] %s", error_type, message)
                return

        logger.error("AI 调用失败: %s - %s", error_type, error)
