"""Anthropic Provider：调用 Claude API 生成乐评"""

import logging

from mylody.ai.provider_base import BaseProvider

logger = logging.getLogger("mylody.ai.anthropic")


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API 提供商

    Args:
        api_key: Anthropic API 密钥
        model: 模型名称，默认 claude-sonnet-4-20250514
        timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        timeout: int = 15,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def chat(self, system: str, user: str) -> str:
        """调用 Anthropic Claude API

        Args:
            system: 系统 Prompt
            user: 用户 Prompt

        Returns:
            str: Claude 返回的文本响应

        Raises:
            anthropic.AuthenticationError: API Key 无效
            anthropic.RateLimitError: 请求频率超限
            anthropic.APIStatusError: 服务端错误
            asyncio.TimeoutError: 请求超时
        """
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        logger.debug("调用 Anthropic API: model=%s", self._model)

        response = await client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=self._timeout,
        )

        return response.content[0].text
