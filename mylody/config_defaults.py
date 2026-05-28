"""配置默认值定义：内置默认配置与示例配置路径"""

from pathlib import Path


DEFAULT_CONFIG: dict = {
    "ai": {
        "provider": "anthropic",
        "api_key": "YOUR_API_KEY_HERE",
        "model": "claude-sonnet-4-20250514",
        "base_url": "",
        "timeout_seconds": 15,
        "max_retries": 2,
    },
    "cache": {
        "enabled": True,
        "cache_ttl_days": 0,
        "db_path": "",
    },
    "listener": {
        "poll_interval_seconds": 2,
        "debounce_seconds": 3,
        "excluded_apps": [],
    },
    "display": {
        "show_in_tray": True,
        "auto_show_review": True,
        "language": "zh-CN",
    },
    "logging": {
        "level": "INFO",
        "max_file_size_mb": 5,
        "backup_count": 3,
    },
    "server": {
        "host": "127.0.0.1",
        "port": 5800,
    },
}

CONFIG_DIR_NAME = ".mylody"
CONFIG_FILE_NAME = "config.yaml"
EXAMPLE_CONFIG_NAME = "config.example.yaml"


def get_example_config_path() -> Path:
    """获取 config.example.yaml 的绝对路径

    Returns:
        Path: 示例配置文件路径
    """
    return Path(__file__).parent.parent / EXAMPLE_CONFIG_NAME
