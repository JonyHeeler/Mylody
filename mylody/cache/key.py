"""缓存 Key 标准化工具"""

import logging

logger = logging.getLogger("mylody.cache.key")


def normalize_cache_key(artist: str, title: str) -> str:
    """生成标准化的缓存 Key

    规则：{lower(trim(artist))}::{lower(trim(title))}
    artist 为空时降级为 unknown::{title}

    Args:
        artist: 艺术家名称
        title: 歌曲名称

    Returns:
        str: 标准化后的缓存 Key
    """
    artist = (artist or "").strip()
    title = (title or "").strip()

    if not artist:
        return f"unknown::{title.lower()}"

    return f"{artist.lower()}::{title.lower()}"
