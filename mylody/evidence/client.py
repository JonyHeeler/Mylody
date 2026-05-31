"""MusicBrainz API 客户端：统一请求封装"""

import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from mylody.evidence.rate_limiter import RateLimiter

logger = logging.getLogger("mylody.evidence.client")

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
COVER_ART_BASE_URL = "https://coverartarchive.org"

USER_AGENT = "Mylody/0.1.0 ( jonywang317@gmail.com )"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}


class MusicBrainzError(Exception):
    """MusicBrainz 请求错误基类"""


class NotFoundError(MusicBrainzError):
    """资源不存在"""


class RateLimitError(MusicBrainzError):
    """被限流"""


class ServiceError(MusicBrainzError):
    """服务错误"""


class MusicBrainzClient:
    """MusicBrainz API 客户端

    所有请求经过限流器，自动设置 User-Agent 和 Accept headers。

    Attributes:
        _limiter: 限流器实例
        _client: HTTP 客户端
    """

    def __init__(self) -> None:
        self._limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    async def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        base_url: str = MUSICBRAINZ_BASE_URL,
    ) -> dict:
        """发送 GET 请求

        Args:
            path: API 路径
            params: 查询参数
            base_url: 基础 URL

        Returns:
            dict: JSON 响应

        Raises:
            NotFoundError: 资源不存在
            RateLimitError: 被限流
            ServiceError: 服务错误
        """
        if params is None:
            params = {}

        if base_url == MUSICBRAINZ_BASE_URL:
            params["fmt"] = "json"

        url = f"{base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        async def _do_request() -> dict:
            logger.debug("请求: %s", url)
            response = await self._client.get(url)

            if response.status_code == 404:
                raise NotFoundError(f"资源不存在: {path}")

            if response.status_code == 503:
                raise RateLimitError("MusicBrainz 限流或服务不可用")

            if response.status_code >= 400:
                raise ServiceError(
                    f"MusicBrainz 请求失败: {response.status_code}"
                )

            return response.json()

        return await self._limiter.run(_do_request)

    async def get_cover_art(self, release_mbid: str) -> Optional[dict]:
        """获取封面图

        Args:
            release_mbid: Release MusicBrainz ID

        Returns:
            Optional[dict]: 封面图信息，不存在返回 None
        """
        try:
            return await self.get(
                f"/release/{release_mbid}",
                base_url=COVER_ART_BASE_URL,
            )
        except NotFoundError:
            return None

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()
