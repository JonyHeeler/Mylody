"""配置管理模块：加载、验证、提供 YAML 配置访问"""

import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from mylody.config_defaults import DEFAULT_CONFIG, get_example_config_path


class Config:
    """Mylody 配置管理器

    负责从项目根目录 config.yaml 加载配置，处理缺失字段和异常情况。

    Args:
        config_path: 自定义配置文件路径，为 None 时使用默认路径
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._path = Path(config_path) if config_path else self._default_config_path()
        self._data: dict = {}
        self._load()

    @staticmethod
    def _default_config_path() -> Path:
        """Return the config.yaml path in the project root."""
        return Path(__file__).parent.parent / "config.yaml"

    def _load(self) -> None:
        """加载配置：确保配置文件存在，读取并合并默认值"""
        self._ensure_config_file()
        user_config = self._load_yaml(self._path)
        self._data = self._merge(DEFAULT_CONFIG, user_config)

    def _ensure_config_file(self) -> None:
        """若 config.yaml 不存在，从 config.example.yaml 复制"""
        if self._path.exists():
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        example = get_example_config_path()
        if example.exists():
            text = example.read_text(encoding="utf-8")
            self._path.write_text(text, encoding="utf-8")
            print(f"[Mylody] 已创建配置文件: {self._path}")
            print("[Mylody] 请编辑配置文件，填写你的 API Key")
        else:
            self._path.write_text(yaml.dump(DEFAULT_CONFIG, allow_unicode=True), encoding="utf-8")
            print(f"[Mylody] 已生成默认配置: {self._path}")

    def _load_yaml(self, path: Path) -> dict:
        """读取 YAML 配置文件

        Args:
            path: YAML 文件路径

        Returns:
            dict: 解析后的配置字典
        """
        try:
            text = path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            print(f"[Mylody] 配置文件 YAML 语法错误: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[Mylody] 读取配置文件失败: {e}", file=sys.stderr)
            return {}

    def _merge(self, defaults: dict, overrides: dict) -> dict:
        """深度合并：以 defaults 为基础，用 overrides 覆盖

        Args:
            defaults: 默认配置
            overrides: 用户配置

        Returns:
            dict: 合并后的配置
        """
        result = defaults.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键

        Args:
            key: 配置键名，如 "ai.model" 或 "listener.debounce_seconds"
            default: 键不存在时的默认值

        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def validate(self) -> list[str]:
        """验证配置有效性

        Returns:
            list[str]: 警告信息列表，空列表表示配置有效
        """
        warnings = []
        api_key = self.get("ai.api_key", "")
        if not api_key or api_key in ("YOUR_API_KEY_HERE", "YOUR_MIMO_API_KEY"):
            warnings.append(f"API Key 未配置，请编辑 {self._path} 填写有效的 API Key")
        if not self.get("ai.base_url", ""):
            warnings.append("ai.base_url 未配置；DeepSeek 可使用 https://api.deepseek.com")
        if not self.get("ai.model", ""):
            warnings.append("ai.model 未配置")
        return warnings

    @property
    def data(self) -> dict:
        """获取完整配置字典

        Returns:
            dict: 当前配置数据
        """
        return self._data

    @property
    def path(self) -> Path:
        """获取配置文件路径

        Returns:
            Path: 配置文件路径
        """
        return self._path
