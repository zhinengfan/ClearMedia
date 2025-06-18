"""
后台扫描器任务的异步单元测试

测试后台扫描任务的生命周期管理，包括启动、运行、停止等功能。
使用pytest-asyncio进行异步测试，模拟scan_directory_once以隔离测试。
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.scanner import background_scanner_task


class TestBackgroundScannerTask:
    """测试background_scanner_task异步函数"""
    
    @pytest.fixture
    def mock_settings(self):
        """创建模拟的配置对象"""
        settings = MagicMock(spec=Settings)
        settings.SOURCE_DIR = Path("/test/source")
        settings.SCAN_INTERVAL_SECONDS = 1  # 使用短间隔以加快测试
        settings.VIDEO_EXTENSIONS = ".mp4,.mkv,.avi,.mov"  # 添加视频扩展名配置
        return settings
    
    @pytest.fixture
    def mock_db_session_factory(self):
        """创建模拟的数据库会话工厂"""
        mock_session = MagicMock()
        
        def session_factory():
            return mock_session
        
        return session_factory
    
    @pytest.fixture
    def stop_event(self):
        """创建停止事件fixture"""
        return asyncio.Event()
    
    @pytest.mark.asyncio
    async def test_background_scanner_starts_and_stops_gracefully(
        self, mock_db_session_factory, mock_settings, stop_event, mocker
    ):
        """测试后台扫描任务的优雅启动和停止"""
        # 模拟scan_directory_once函数
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.return_value = 2  # 模拟发现2个新文件
        
        # 启动后台任务
        task = asyncio.create_task(
            background_scanner_task(mock_db_session_factory, mock_settings, stop_event)
        )
        
        # 等待一小段时间确保任务开始运行
        await asyncio.sleep(0.1)
        
        # 验证任务正在运行
        assert not task.done()
        
        # 设置停止事件
        stop_event.set()
        
        # 等待任务完成
        await asyncio.wait_for(task, timeout=2.0)
        
        # 验证任务正常结束
        assert task.done()
        assert not task.cancelled()
    
    @pytest.mark.asyncio
    async def test_background_scanner_calls_scan_function_periodically(
        self, mock_db_session_factory, mock_settings, stop_event, mocker
    ):
        """测试后台扫描任务定期调用扫描函数"""
        # 模拟scan_directory_once函数
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.return_value = 1
        
        # 启动后台任务
        task = asyncio.create_task(
            background_scanner_task(mock_db_session_factory, mock_settings, stop_event)
        )
        
        # 等待足够时间以执行至少2次扫描
        await asyncio.sleep(2.5)  # 超过2个扫描间隔
        
        # 停止任务
        stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        
        # 验证扫描函数被调用了至少2次
        assert mock_scan.call_count >= 2
        
        # 验证调用参数正确
        for call in mock_scan.call_args_list:
            args, kwargs = call
            assert len(args) == 3  # db_session, source_dir, allowed_extensions
            assert args[1] == mock_settings.SOURCE_DIR  # source_dir
            assert isinstance(args[2], set)  # allowed_extensions
    
    @pytest.mark.asyncio
    async def test_background_scanner_handles_scan_exceptions(
        self, mock_db_session_factory, mock_settings, stop_event, mocker
    ):
        """测试后台扫描任务处理扫描异常"""
        # 模拟scan_directory_once抛出异常
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.side_effect = Exception("模拟扫描错误")
        
        # 启动后台任务
        task = asyncio.create_task(
            background_scanner_task(mock_db_session_factory, mock_settings, stop_event)
        )
        
        # 等待一段时间确保异常被处理
        await asyncio.sleep(1.5)
        
        # 验证任务仍在运行（异常被捕获）
        assert not task.done()
        
        # 停止任务
        stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        
        # 验证扫描函数被调用（尽管有异常）
        assert mock_scan.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_background_scanner_with_no_stop_event(
        self, mock_db_session_factory, mock_settings, mocker
    ):
        """测试后台扫描任务在没有提供stop_event时的行为"""
        # 模拟scan_directory_once函数
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.return_value = 0
        
        # 启动后台任务（不提供stop_event）
        task = asyncio.create_task(
            background_scanner_task(mock_db_session_factory, mock_settings)
        )
        
        # 等待一小段时间确保任务开始运行
        await asyncio.sleep(0.1)
        
        # 验证任务正在运行
        assert not task.done()
        
        # 取消任务（模拟外部取消）
        task.cancel()
        
        # 等待任务被取消
        with pytest.raises(asyncio.CancelledError):
            await task
        
        # 验证任务被取消
        assert task.cancelled()
    
    @pytest.mark.asyncio
    async def test_background_scanner_session_factory_usage(
        self, mock_settings, stop_event, mocker
    ):
        """测试后台扫描任务正确使用数据库会话工厂"""
        # 创建具有上下文管理器的模拟会话
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        # 创建会话工厂
        session_factory = MagicMock(return_value=mock_session)
        
        # 模拟scan_directory_once函数
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.return_value = 0
        
        # 启动后台任务
        task = asyncio.create_task(
            background_scanner_task(session_factory, mock_settings, stop_event)
        )
        
        # 等待一次扫描完成
        await asyncio.sleep(1.2)
        
        # 停止任务
        stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        
        # 验证会话工厂被调用
        assert session_factory.call_count >= 1
        
        # 验证会话的上下文管理器被正确使用
        assert mock_session.__enter__.call_count >= 1
        assert mock_session.__exit__.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_background_scanner_respects_scan_interval(
        self, mock_db_session_factory, mock_settings, stop_event, mocker
    ):
        """测试后台扫描任务遵守扫描间隔"""
        # 设置较长的扫描间隔
        mock_settings.SCAN_INTERVAL_SECONDS = 2
        
        # 模拟scan_directory_once函数
        mock_scan = mocker.patch('app.scanner.scan_directory_once')
        mock_scan.return_value = 0
        
        # 记录开始时间
        start_time = asyncio.get_event_loop().time()
        
        # 启动后台任务
        task = asyncio.create_task(
            background_scanner_task(mock_db_session_factory, mock_settings, stop_event)
        )
        
        # 等待足够时间进行第一次扫描，但不足以进行第二次
        await asyncio.sleep(1.0)
        
        # 此时应该只执行了一次扫描
        first_scan_count = mock_scan.call_count
        assert first_scan_count == 1
        
        # 再等待足够时间进行第二次扫描
        await asyncio.sleep(1.5)
        
        # 验证第二次扫描已执行
        assert mock_scan.call_count >= 2
        
        # 停止任务
        stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        
        # 验证总执行时间合理（至少2秒用于间隔）
        total_time = asyncio.get_event_loop().time() - start_time
        assert total_time >= 2.0 