"""Debouncer 单元测试"""

import asyncio

import pytest

from mylody.listener.debounce import Debouncer


@pytest.fixture
def mock_callback():
    """创建模拟回调函数"""
    results = []

    async def callback(data):
        results.append(data)

    return callback, results


@pytest.mark.asyncio
async def test_debounce_normal_trigger(mock_callback):
    """测试正常触发"""
    callback, results = mock_callback
    debouncer = Debouncer(delay_seconds=0.1, callback=callback)

    await debouncer.trigger("test_data")
    await asyncio.sleep(0.2)

    assert len(results) == 1
    assert results[0] == "test_data"


@pytest.mark.asyncio
async def test_debounce_cancel_previous(mock_callback):
    """测试连续调用取消前一次"""
    callback, results = mock_callback
    debouncer = Debouncer(delay_seconds=0.2, callback=callback)

    await debouncer.trigger("first")
    await asyncio.sleep(0.05)
    await debouncer.trigger("second")
    await asyncio.sleep(0.3)

    assert len(results) == 1
    assert results[0] == "second"


@pytest.mark.asyncio
async def test_debounce_callback_exception(mock_callback):
    """测试回调异常处理"""
    call_count = 0

    async def failing_callback(data):
        nonlocal call_count
        call_count += 1
        raise ValueError("Test error")

    debouncer = Debouncer(delay_seconds=0.1, callback=failing_callback)

    await debouncer.trigger("test_data")
    await asyncio.sleep(0.2)

    assert call_count == 1


@pytest.mark.asyncio
async def test_debounce_is_pending(mock_callback):
    """测试 is_pending 属性"""
    callback, results = mock_callback
    debouncer = Debouncer(delay_seconds=0.2, callback=callback)

    assert debouncer.is_pending is False

    await debouncer.trigger("test_data")
    assert debouncer.is_pending is True

    await asyncio.sleep(0.3)
    assert debouncer.is_pending is False


@pytest.mark.asyncio
async def test_debounce_cancel(mock_callback):
    """测试取消功能"""
    callback, results = mock_callback
    debouncer = Debouncer(delay_seconds=0.2, callback=callback)

    await debouncer.trigger("test_data")
    debouncer.cancel()

    await asyncio.sleep(0.3)

    assert len(results) == 0
    assert debouncer.is_pending is False
