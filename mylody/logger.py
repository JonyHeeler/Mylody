"""日志系统：同时输出到控制台和文件，支持日志轮转"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mylody.utils.paths import get_log_dir


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "mylody.log"


def setup_logger(
    level: str = "INFO",
    max_file_size_mb: int = 5,
    backup_count: int = 3,
) -> logging.Logger:
    """初始化 Mylody 日志系统

    同时输出到控制台和文件，文件按大小自动轮转。

    Args:
        level: 日志级别（DEBUG / INFO / WARNING / ERROR）
        max_file_size_mb: 单个日志文件最大大小（MB）
        backup_count: 保留的旧日志文件数量

    Returns:
        logging.Logger: 配置好的根日志记录器
    """
    logger = logging.getLogger("mylody")
    logger.setLevel(_parse_level(level))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = get_log_dir()
    log_file = log_dir / LOG_FILE_NAME
    file_handler = _create_file_handler(log_file, formatter, max_file_size_mb, backup_count)
    logger.addHandler(file_handler)

    return logger


def _create_file_handler(
    log_file: Path,
    formatter: logging.Formatter,
    max_file_size_mb: int,
    backup_count: int,
) -> RotatingFileHandler:
    """创建文件日志处理器

    Args:
        log_file: 日志文件路径
        formatter: 日志格式化器
        max_file_size_mb: 单文件最大大小（MB）
        backup_count: 备份文件数量

    Returns:
        RotatingFileHandler: 文件处理器
    """
    max_bytes = max_file_size_mb * 1024 * 1024
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


def _parse_level(level_str: str) -> int:
    """将字符串日志级别转换为 logging 常量

    Args:
        level_str: 日志级别字符串

    Returns:
        int: logging 模块的日志级别常量
    """
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    return mapping.get(level_str.upper(), logging.INFO)
