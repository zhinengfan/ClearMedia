"""测试后台扫描任务的异步行为"""

import asyncio
from unittest.mock import MagicMock, patch
import pytest
from app.services.media.scanner import background_scanner_task


class TestBackgroundScannerTask:
    """测试 background_scanner_task 异步函数"""
    
    @pytest.mark.asyncio
    async def test_background_scanner_task_basic_cycle(self):
        """测试后台扫描任务的基本循环功能"""
        # 模拟设置对象
        mock_settings = MagicMock()
        mock_settings.SOURCE_DIR = "/test/source"
        mock_settings.SCAN_INTERVAL_SECONDS = 0.1  # 很短的间隔用于测试
        mock_settings.VIDEO_EXTENSIONS = "mp4,mkv"
        
        # 模拟数据库会话工厂
        mock_db_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_db_session_factory.return_value.__enter__.return_value = mock_session
        
        # 创建队列和停止事件
        media_queue = asyncio.Queue()
        stop_event = asyncio.Event()
        
        # 模拟 scan_directory_once 返回一些文件ID
        with patch('app.services.media.scanner.scan_directory_once', return_value=[123, 456]):
            # 启动后台任务
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event,
                    media_queue=media_queue
                )
            )
            
            # 等待任务执行一次扫描
            await asyncio.sleep(0.15)  # 稍微长于 SCAN_INTERVAL_SECONDS
            
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
            
            # 验证队列中有预期的文件ID
            assert not media_queue.empty()
            file_ids = []
            while not media_queue.empty():
                file_ids.append(await media_queue.get())
            
            assert 123 in file_ids
            assert 456 in file_ids
    
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
        """测试没有队列时的行为"""
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
            # 启动后台任务（没有传递 media_queue）
            task = asyncio.create_task(
                background_scanner_task(
                    mock_db_session_factory,
                    mock_settings,
                    stop_event
                    # 注意：没有传递 media_queue
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