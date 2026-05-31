"""MediaListener 单元测试"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mylody.listener import MediaListener
from mylody.types import MediaInfo


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "listener.debounce_seconds": 0.1,
        "listener.poll_interval_seconds": 0.1,
        "listener.excluded_apps": ["chrome.exe"],
    }.get(key, default)
    return config


@pytest.fixture
def mock_media_session():
    """创建模拟 MediaSessionManager"""
    with patch("mylody.listener.MediaSessionManager") as mock_class:
        mock_instance = MagicMock()
        mock_instance.initialize = AsyncMock(return_value=True)
        mock_instance.get_current_info = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_listener_start_stop(mock_config, mock_media_session):
    """测试监听器启动和停止"""
    callback = AsyncMock()
    listener = MediaListener(mock_config, callback)

    await listener.start()
    assert listener._running is True

    await listener.stop()
    assert listener._running is False


@pytest.mark.asyncio
async def test_listener_track_change_detection(mock_config, mock_media_session):
    """测试曲目变化检测"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="Test Artist",
        source_app="Spotify.exe",
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    callback.assert_called_once_with(track_info)


@pytest.mark.asyncio
async def test_listener_excluded_app(mock_config, mock_media_session):
    """测试排除应用过滤"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="Test Artist",
        source_app="chrome.exe",
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = True

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_listener_same_track_no_trigger(mock_config, mock_media_session):
    """测试相同曲目不触发"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="Test Artist",
        source_app="Spotify.exe",
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    assert callback.call_count == 1


@pytest.mark.asyncio
async def test_listener_no_media(mock_config, mock_media_session):
    """测试无媒体播放"""
    callback = AsyncMock()

    mock_media_session.get_current_info.return_value = None

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    callback.assert_not_called()
    assert listener.current_track is None


@pytest.mark.asyncio
async def test_listener_clears_track_when_media_stops(mock_config, mock_media_session):
    """测试已有曲目停止后通知上层清空状态"""
    callback = AsyncMock()
    clear_callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="Test Artist",
        source_app="Spotify.exe",
        playback_status=4,
    )

    mock_media_session.get_current_info.side_effect = [track_info, track_info, None, None]
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback, on_track_clear=clear_callback)

    await listener.start()
    await asyncio.sleep(0.5)
    await listener.stop()

    callback.assert_called_once_with(track_info)
    clear_callback.assert_called_once()
    assert listener.current_track is None


@pytest.mark.asyncio
async def test_listener_ignores_invalid_unknown_track(mock_config, mock_media_session):
    """测试未知占位曲目不触发乐评"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="未知歌曲",
        artist="未知艺术家",
        source_app="Spotify.exe",
        playback_status=4,
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    callback.assert_not_called()
    assert listener.current_track is None


@pytest.mark.asyncio
async def test_listener_allows_known_title_with_unknown_artist(mock_config, mock_media_session):
    """测试标题有效时允许歌手缺失"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="未知艺术家",
        source_app="Spotify.exe",
        playback_status=4,
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback)

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    callback.assert_called_once_with(track_info)


@pytest.mark.asyncio
async def test_listener_current_track_property(mock_config, mock_media_session):
    """测试 current_track 属性"""
    callback = AsyncMock()
    track_info = MediaInfo(
        title="Test Song",
        artist="Test Artist",
        source_app="Spotify.exe",
    )

    mock_media_session.get_current_info.return_value = track_info
    mock_media_session.is_excluded.return_value = False

    listener = MediaListener(mock_config, callback)

    assert listener.current_track is None

    await listener.start()
    await asyncio.sleep(0.3)
    await listener.stop()

    assert listener.current_track is not None
    assert listener.current_track.title == "Test Song"
