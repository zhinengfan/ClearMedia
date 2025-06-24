"""测试后台扫描任务的异步行为"""

import asyncio
from unittest.mock import MagicMock, patch
import pytest
from app.services.media.scanner import background_scanner_task


class TestBackgroundScannerTask:
    """测试 background_scanner_task 异步函数"""
    
    @pytest.mark.asyncio
    async def test_background_scanner_task_graceful_stop(self):
        """测试后台扫描任务的优雅停止"""
        # 模拟设置对象
        mock_settings = MagicMock()
        mock_settings.SOURCE_DIR = "/test/source"
        mock_settings.SCAN_INTERVAL_SECONDS = 0.1
        mock_settings.VIDEO_EXTENSIONS = "mp4"
        
        # 模拟数据库会话工厂
        mock_db_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_db_session_factory.return_value.__enter__.return_value = mock_session
        
        # 创建停止事件
        stop_event = asyncio.Event()
        
        # 模拟 scan_directory_once 返回空列表
        with patch('app.services.media.scanner.scan_directory_once', return_value=[]):
            # 启动后台任务
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event
                )
            )
            
            # 让任务运行一小段时间
            await asyncio.sleep(0.05)
            
            # 触发停止事件
            stop_event.set()
            
            # 等待任务完成（应该在下一次循环检查时退出）
            await asyncio.sleep(0.15)
            
            # 任务应该已经自然结束
            assert task.done()
    
    @pytest.mark.asyncio
    async def test_background_scanner_task_no_queue(self):
        """测试没有队列时的行为 - 新架构下的正常场景"""
        # 模拟设置对象
        mock_settings = MagicMock()
        mock_settings.SOURCE_DIR = "/test/source"
        mock_settings.SCAN_INTERVAL_SECONDS = 0.1
        mock_settings.VIDEO_EXTENSIONS = "mp4"
        
        # 模拟数据库会话工厂
        mock_db_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_db_session_factory.return_value.__enter__.return_value = mock_session
        
        # 创建停止事件
        stop_event = asyncio.Event()
        
        # 模拟 scan_directory_once 返回一些文件ID
        with patch('app.services.media.scanner.scan_directory_once', return_value=[789]):
            # 启动后台任务（没有传递 media_queue，这是新架构下的正常情况）
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event
                    # 注意：没有传递 media_queue，这在新架构下是正常的
                )
            )
            
            # 让任务运行一小段时间
            await asyncio.sleep(0.15)
            
            # 触发停止事件
            stop_event.set()
            
            # 等待任务完成
            await asyncio.sleep(0.15)
            
            # 任务应该正常结束，不应该抛出异常
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    @pytest.mark.asyncio
    async def test_background_scanner_task_scan_exception(self):
        """测试扫描过程中出现异常的处理"""
        # 模拟设置对象
        mock_settings = MagicMock()
        mock_settings.SOURCE_DIR = "/test/source"
        mock_settings.SCAN_INTERVAL_SECONDS = 0.1
        mock_settings.VIDEO_EXTENSIONS = "mp4"
        
        # 模拟数据库会话工厂
        mock_db_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_db_session_factory.return_value.__enter__.return_value = mock_session
        
        # 创建停止事件
        stop_event = asyncio.Event()
        
        # 模拟 scan_directory_once 抛出异常
        with patch('app.services.media.scanner.scan_directory_once', side_effect=Exception("Scan error")):
            # 启动后台任务
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event
                )
            )
            
            # 让任务运行一小段时间（即使有异常也应该继续）
            await asyncio.sleep(0.15)
            
            # 触发停止事件
            stop_event.set()
            
            # 等待任务完成
            await asyncio.sleep(0.15)
            
            # 任务应该正常结束，异常被捕获并记录
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_background_scanner_task_database_operations(self):
        """测试后台扫描任务的数据库操作调用"""
        # 模拟设置对象
        mock_settings = MagicMock()
        mock_settings.SOURCE_DIR = "/test/source"
        mock_settings.SCAN_INTERVAL_SECONDS = 0.1
        mock_settings.VIDEO_EXTENSIONS = "mp4,mkv"
        
        # 模拟数据库会话工厂
        mock_db_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_db_session_factory.return_value.__enter__.return_value = mock_session
        
        # 创建停止事件
        stop_event = asyncio.Event()
        
        # 模拟 scan_directory_once 返回一些文件ID
        with patch('app.services.media.scanner.scan_directory_once', return_value=[123, 456]) as mock_scan:
            # 启动后台任务
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event
                )
            )
            
            # 等待任务执行一次扫描
            await asyncio.sleep(0.15)
            
            # 触发停止事件
            stop_event.set()
            
            # 等待任务完成
            await asyncio.sleep(0.15)
            
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # 验证 scan_directory_once 被调用
            mock_scan.assert_called()
            # 验证调用时使用了正确的参数类型
            call_args = mock_scan.call_args[0]
            assert call_args[0] == mock_session  # db_session
            assert call_args[1] == mock_settings  # settings
            assert isinstance(call_args[2], set)  # allowed_extensions should be a set 