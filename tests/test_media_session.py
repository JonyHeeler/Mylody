"""MediaSessionManager 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mylody.listener.media_session import MediaSessionManager
from mylody.types import MediaInfo


@pytest.fixture
def media_session():
    """创建 MediaSessionManager 实例"""
    return MediaSessionManager()


@pytest.fixture
def mock_winrt():
    """创建 WinRT 模拟对象"""
    with patch("mylody.listener.media_session.MediaSessionManager") as mock:
        yield mock


def test_initial_state(media_session):
    """测试初始状态"""
    assert media_session._initialized is False
    assert media_session._manager is None


@pytest.mark.asyncio
async def test_initialize_success(media_session):
    """测试初始化成功"""
    mock_manager = AsyncMock()
    mock_manager_class = AsyncMock()
    mock_manager_class.request_async.return_value = mock_manager

    with patch.dict("sys.modules", {"winsdk.windows.media.control": MagicMock(
        GlobalSystemMediaTransportControlsSessionManager=mock_manager_class
    )}):
        result = await media_session.initialize()

    assert result is True
    assert media_session._initialized is True
    assert media_session._manager == mock_manager


@pytest.mark.asyncio
async def test_initialize_failure(media_session):
    """测试初始化失败"""
    with patch.dict("sys.modules", {"winsdk": None}):
        result = await media_session.initialize()

    assert result is False
    assert media_session._initialized is False


@pytest.mark.asyncio
async def test_get_current_info_no_session(media_session):
    """测试获取信息 - 无媒体会话"""
    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = None

    result = await media_session.get_current_info()

    assert result is None


@pytest.mark.asyncio
async def test_get_current_info_with_session(media_session):
    """测试获取信息 - 有媒体会话"""
    mock_session = MagicMock()
    mock_props = MagicMock()
    mock_props.title = "Test Song"
    mock_props.artist = "Test Artist"
    mock_props.album_title = "Test Album"
    mock_props.album_artist = "Test Album Artist"

    mock_playback = MagicMock()
    mock_playback.playback_status = 4

    mock_session.try_get_media_properties_async = AsyncMock(return_value=mock_props)
    mock_session.get_playback_info.return_value = mock_playback
    mock_session.source_app_user_model_id = "TestApp"

    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = mock_session

    result = await media_session.get_current_info()

    assert result is not None
    assert result.title == "Test Song"
    assert result.artist == "Test Artist"
    assert result.album == "Test Album"
    assert result.source_app == "TestApp"
    assert result.playback_status == 4


@pytest.mark.asyncio
async def test_get_current_info_splits_apple_music_artist_album(media_session):
    """测试 Apple Music 把 artist 写成 artist — album 时能拆分"""
    mock_session = MagicMock()
    mock_props = MagicMock()
    mock_props.title = "All We Are"
    mock_props.artist = "OneRepublic — Dreaming Out Loud (Deluxe)"
    mock_props.album_title = ""
    mock_props.album_artist = "OneRepublic"
    mock_props.track_number = 7
    mock_props.album_track_count = 16
    mock_props.genres = ["Pop"]

    mock_playback = MagicMock()
    mock_playback.playback_status = 4
    mock_timeline = MagicMock()
    mock_timeline.end_time = 2450000000
    mock_timeline.position = 300000000

    mock_session.try_get_media_properties_async = AsyncMock(return_value=mock_props)
    mock_session.get_playback_info.return_value = mock_playback
    mock_session.get_timeline_properties.return_value = mock_timeline
    mock_session.source_app_user_model_id = "AppleMusic"

    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = mock_session

    result = await media_session.get_current_info()

    assert result is not None
    assert result.artist == "OneRepublic"
    assert result.album == "Dreaming Out Loud (Deluxe)"
    assert result.track_number == 7
    assert result.album_track_count == 16
    assert result.genres == ["Pop"]
    assert result.duration_ms == 245000


@pytest.mark.asyncio
async def test_get_current_info_ignores_empty_title(media_session):
    """测试获取信息 - 空标题不应被当作歌曲"""
    mock_session = MagicMock()
    mock_props = MagicMock()
    mock_props.title = ""
    mock_props.artist = ""
    mock_props.album_title = ""
    mock_props.album_artist = ""

    mock_playback = MagicMock()
    mock_playback.playback_status = 4

    mock_session.try_get_media_properties_async = AsyncMock(return_value=mock_props)
    mock_session.get_playback_info.return_value = mock_playback
    mock_session.source_app_user_model_id = "TestApp"

    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = mock_session

    result = await media_session.get_current_info()

    assert result is None


@pytest.mark.asyncio
async def test_get_current_info_allows_missing_artist(media_session):
    """测试获取信息 - 标题有效时允许歌手缺失"""
    mock_session = MagicMock()
    mock_props = MagicMock()
    mock_props.title = "Test Song"
    mock_props.artist = ""
    mock_props.album_title = "Test Album"
    mock_props.album_artist = ""

    mock_playback = MagicMock()
    mock_playback.playback_status = 4

    mock_session.try_get_media_properties_async = AsyncMock(return_value=mock_props)
    mock_session.get_playback_info.return_value = mock_playback
    mock_session.source_app_user_model_id = "TestApp"

    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = mock_session

    result = await media_session.get_current_info()

    assert result is not None
    assert result.title == "Test Song"
    assert result.artist == "未知艺术家"


@pytest.mark.asyncio
async def test_get_current_info_ignores_paused_media(media_session):
    """测试获取信息 - 暂停状态不触发当前播放"""
    mock_session = MagicMock()
    mock_props = MagicMock()
    mock_props.title = "Test Song"
    mock_props.artist = "Test Artist"
    mock_props.album_title = "Test Album"
    mock_props.album_artist = "Test Album Artist"

    mock_playback = MagicMock()
    mock_playback.playback_status = 5

    mock_session.try_get_media_properties_async = AsyncMock(return_value=mock_props)
    mock_session.get_playback_info.return_value = mock_playback
    mock_session.source_app_user_model_id = "TestApp"

    media_session._initialized = True
    media_session._manager = MagicMock()
    media_session._manager.get_current_session.return_value = mock_session

    result = await media_session.get_current_info()

    assert result is None


@pytest.mark.asyncio
async def test_get_current_info_not_initialized(media_session):
    """测试获取信息 - 未初始化"""
    result = await media_session.get_current_info()
    assert result is None


def test_is_excluded_not_in_list(media_session):
    """测试进程过滤 - 不在排除列表"""
    media_info = MediaInfo(source_app="Spotify.exe")
    excluded_apps = ["chrome.exe", "firefox.exe"]

    result = media_session.is_excluded(media_info, excluded_apps)

    assert result is False


def test_is_excluded_in_list(media_session):
    """测试进程过滤 - 在排除列表"""
    media_info = MediaInfo(source_app="Spotify.exe")
    excluded_apps = ["spotify", "chrome.exe"]

    result = media_session.is_excluded(media_info, excluded_apps)

    assert result is True


def test_is_excluded_empty_source(media_session):
    """测试进程过滤 - 空来源应用"""
    media_info = MediaInfo(source_app="")
    excluded_apps = ["spotify"]

    result = media_session.is_excluded(media_info, excluded_apps)

    assert result is False


def test_is_excluded_case_insensitive(media_session):
    """测试进程过滤 - 大小写不敏感"""
    media_info = MediaInfo(source_app="Spotify.exe")
    excluded_apps = ["SPOTIFY"]

    result = media_session.is_excluded(media_info, excluded_apps)

    assert result is True
