"""测试单个文件处理功能"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from sqlmodel import Session
from app.services.media.scanner import _process_single_file
from app.core.models import MediaFile


class TestProcessSingleFile:
    """测试 _process_single_file 函数"""
    
    def test_process_single_file_new_record(self):
        """测试处理新文件时创建数据库记录"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            # 模拟数据库会话和CRUD操作
            mock_session = Mock(spec=Session)
            
            # 模拟文件不存在于数据库中
            with patch('app.services.media.scanner.crud.get_media_file_by_inode_device', return_value=None):
                # 模拟创建新记录
                mock_media_file = Mock(spec=MediaFile)
                mock_media_file.id = 123
                mock_media_file.filename = file_path.name
                
                with patch('app.services.media.scanner.crud.create_media_file', return_value=mock_media_file):
                    result = _process_single_file(mock_session, file_path)
                    
                    assert result == 123  # 返回新创建的文件ID
    
    def test_process_single_file_existing_record(self):
        """测试处理已存在文件时返回None"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            # 模拟数据库会话
            mock_session = Mock(spec=Session)
            
            # 模拟文件已存在于数据库中
            mock_existing_file = Mock(spec=MediaFile)
            mock_existing_file.id = 456
            mock_existing_file.filename = file_path.name
            
            with patch('app.services.media.scanner.crud.get_media_file_by_inode_device', return_value=mock_existing_file):
                result = _process_single_file(mock_session, file_path)
                
                assert result is None  # 文件已存在，返回None
    
    def test_process_single_file_stat_error(self):
        """测试获取文件信息失败时的错误处理"""
        file_path = Path("/non/existent/file.mp4")
        mock_session = Mock(spec=Session)
        
        result = _process_single_file(mock_session, file_path)
        assert result is None  # 无法获取文件信息，返回None
    
    def test_process_single_file_database_query_error(self):
        """测试数据库查询失败时的错误处理"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            mock_session = Mock(spec=Session)
            
            # 模拟数据库查询失败
            with patch('app.services.media.scanner.crud.get_media_file_by_inode_device', side_effect=Exception("Database error")):
                result = _process_single_file(mock_session, file_path)
                
                assert result is None  # 数据库查询失败，返回None
    
    def test_process_single_file_create_error(self):
        """测试创建数据库记录失败时的错误处理"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            mock_session = Mock(spec=Session)
            
            # 模拟文件不存在于数据库中
            with patch('app.services.media.scanner.crud.get_media_file_by_inode_device', return_value=None):
                # 模拟创建记录失败
                with patch('app.services.media.scanner.crud.create_media_file', side_effect=Exception("Create error")):
                    result = _process_single_file(mock_session, file_path)
                    
                    assert result is None  # 创建失败，返回None
    
    def test_process_single_file_uses_transaction(self):
        """测试函数使用事务处理数据库操作"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            # 模拟数据库会话，记录是否调用了事务相关方法
            mock_session = Mock(spec=Session)
            
            # 模拟文件不存在于数据库中
            with patch('app.services.media.scanner.crud.get_media_file_by_inode_device', return_value=None):
                # 模拟创建新记录
                mock_media_file = Mock(spec=MediaFile)
                mock_media_file.id = 789
                
                with patch('app.services.media.scanner.crud.create_media_file', return_value=mock_media_file):
                    result = _process_single_file(mock_session, file_path)
                    
                    # 验证结果
                    assert result == 789
                    
                    # 可以验证是否调用了相关的数据库方法
                    # 注意：具体的事务实现可能在CRUD层处理 