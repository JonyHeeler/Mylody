"""Config path tests."""

from pathlib import Path

from mylody.config import Config
from mylody.utils.paths import get_config_path


def test_default_config_path_uses_project_root():
    """测试默认配置路径固定为项目根目录 config.yaml"""
    expected = Path(__file__).parent.parent / "config.yaml"

    assert Config._default_config_path() == expected
    assert get_config_path() == expected
