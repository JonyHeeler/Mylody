"""数据脱敏工具：处理敏感信息的遮蔽显示"""

import copy


SENSITIVE_KEYS = {"api_key", "apikey", "api_secret", "secret", "password", "token"}


def mask_api_key(key: str) -> str:
    """将 API Key 脱敏显示，只保留前4后4位

    Args:
        key: 原始 API Key

    Returns:
        str: 脱敏后的字符串，如 "sk-a1b2****xyz9"
    """
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def sanitize_config(config: dict) -> dict:
    """递归脱敏配置中的敏感字段

    Args:
        config: 原始配置字典

    Returns:
        dict: 脱敏后的配置副本
    """
    result = copy.deepcopy(config)
    _sanitize_recursive(result)
    return result


def _sanitize_recursive(data: dict) -> None:
    """递归遍历字典，对敏感字段进行脱敏

    Args:
        data: 要处理的字典（原地修改）
    """
    for key, value in data.items():
        if isinstance(value, dict):
            _sanitize_recursive(value)
        elif isinstance(value, str) and key.lower() in SENSITIVE_KEYS:
            if value and value != "YOUR_API_KEY_HERE":
                data[key] = mask_api_key(value)
