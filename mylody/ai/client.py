"""AI 乐评客户端：组装 Prompt → 调用 Provider → 解析 JSON → 返回 ReviewData"""

import json
import logging
from dataclasses import fields
from typing import Optional

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


class AIClient:
    """AI 乐评生成客户端

    负责组装 Prompt、调用 AI Provider、解析 JSON 响应并返回结构化乐评。

    Args:
        config: Mylody 配置对象
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._provider = self._create_provider()

    def _create_provider(self) -> BaseProvider:
        """根据配置创建对应的 AI Provider

        Returns:
            BaseProvider: AI Provider 实例
        """
        provider_name = self._config.get("ai.provider", "anthropic")
        api_key = self._config.get("ai.api_key", "")
        model = self._config.get("ai.model", "")
        base_url = self._config.get("ai.base_url", "")
        timeout = self._config.get("ai.timeout_seconds", 15)

        if provider_name in ("openai", "custom"):
            from mylody.ai.provider_openai import OpenAIProvider

            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o",
                base_url=base_url,
                timeout=timeout,
            )

        from mylody.ai.provider_anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            timeout=timeout,
        )

    async def generate_review(self, track: MediaInfo) -> Optional[ReviewData]:
        """为指定歌曲生成乐评

        Args:
            track: 歌曲媒体信息

        Returns:
            Optional[ReviewData]: 乐评数据，失败时返回 None
        """
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_user_prompt(track)

        logger.info("生成乐评: %s - %s", track.artist, track.title)

        try:
            raw = await self._provider.chat(system_prompt, user_prompt)
        except TimeoutError:
            logger.error("AI 请求超时")
            return None
        except Exception as e:
            self._handle_api_error(e)
            return None

        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> Optional[ReviewData]:
        """解析 AI 返回的 JSON 响应

        Args:
            raw: AI 返回的原始文本

        Returns:
            Optional[ReviewData]: 解析成功返回 ReviewData，失败返回 None
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("AI 返回非 JSON 格式: %s", raw[:200])
            return None

        if not isinstance(data, dict):
            logger.error("AI 返回非字典类型: %s", type(data).__name__)
            return None

        valid_fields = {f.name for f in fields(ReviewData)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}

        try:
            return ReviewData(**filtered)
        except TypeError as e:
            logger.error("构造 ReviewData 失败: %s", e)
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
