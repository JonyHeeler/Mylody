"""OpenAI Provider：调用 OpenAI 兼容接口生成乐评"""

import logging

from mylody.ai.provider_base import BaseProvider

logger = logging.getLogger("mylody.ai.openai")


class OpenAIProvider(BaseProvider):
    """OpenAI 兼容 API 提供商

    支持 OpenAI 官方接口及兼容的第三方服务（如 DeepSeek、Mimo）。

    Args:
        api_key: API 密钥
        model: 模型名称
        base_url: 自定义接口地址（为空时使用 OpenAI 默认地址）
        timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "",
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url or None
        self._timeout = timeout

    async def chat(self, system: str, user: str) -> str:
        """调用 OpenAI 兼容 API

        Args:
            system: 系统 Prompt
            user: 用户 Prompt
        Returns:
            str: 模型返回的文本响应

        Raises:
            openai.AuthenticationError: API Key 无效
            openai.RateLimitError: 请求频率超限
            openai.APIStatusError: 服务端错误
            asyncio.TimeoutError: 请求超时
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

        logger.debug(
            "调用 OpenAI-compatible API: model=%s, base_url=%s",
            self._model,
            self._base_url,
        )

        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout=self._timeout,
        )

        return response.choices[0].message.content or ""
