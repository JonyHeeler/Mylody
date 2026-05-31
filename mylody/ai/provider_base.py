"""Provider 抽象基类：定义统一的 AI 调用接口"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """AI Provider 抽象基类

    所有 AI 提供商实现必须继承此类并实现 chat 方法。
    """

    @abstractmethod
    async def chat(self, system: str, user: str) -> str:
        """发送对话请求并返回原始响应文本

        Args:
            system: 系统 Prompt
            user: 用户 Prompt
        Returns:
            str: AI 返回的原始文本响应

        Raises:
            Exception: 网络错误、API 错误等
        """
        ...
