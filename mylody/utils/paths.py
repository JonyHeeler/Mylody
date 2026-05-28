"""路径工具：统一管理 Mylody 各目录路径"""

from pathlib import Path


def get_mylody_dir() -> Path:
    """获取 Mylody 主目录 ~/.mylody/

    Returns:
        Path: Mylody 主目录路径，不存在时自动创建
    """
    path = Path.home() / ".mylody"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    """获取 config.yaml 文件路径

    Returns:
        Path: 配置文件完整路径
    """
    return get_mylody_dir() / "config.yaml"


def get_cache_dir() -> Path:
    """获取缓存目录路径

    Returns:
        Path: 缓存目录路径，不存在时自动创建
    """
    path = get_mylody_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    """获取日志目录路径

    Returns:
        Path: 日志目录路径，不存在时自动创建
    """
    path = get_mylody_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_example_config_path() -> Path:
    """获取 config.example.yaml 示例配置文件路径

    Returns:
        Path: 示例配置文件路径（项目根目录下）
    """
    return Path(__file__).parent.parent.parent / "config.example.yaml"
