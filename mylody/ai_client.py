"""AI 请求模块骨架：Phase 2 实现完整功能"""

import logging
from typing import Optional

from mylody.types import MediaInfo, ReviewData

logger = logging.getLogger("mylody.ai_client")


class AIClient:
    """AI 乐评生成客户端

    负责构造 Prompt 并调用 AI 接口生成结构化乐评。

    Args:
        provider: AI 提供商（anthropic / openai / custom）
        api_key: API 密钥
        model: 模型名称
        base_url: 自定义接口地址（仅 custom 提供商需要）
        timeout_seconds: 请求超时时间
        max_retries: 失败重试次数
    """

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        timeout_seconds: int = 15,
        max_retries: int = 2,
    ) -> None:
        self._provider = provider
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def generate_review(self, track: MediaInfo) -> Optional[ReviewData]:
        """为指定歌曲生成乐评

        Args:
            track: 歌曲媒体信息

        Returns:
            Optional[ReviewData]: 乐评数据，失败时返回 None
        """
        logger.info("AI 乐评生成将在 Phase 2 实现: %s - %s", track.artist, track.title)
        return None
