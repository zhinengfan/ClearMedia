"""
扫描器模块的单元测试

"""

from pathlib import Path
from unittest.mock import MagicMock



class TestScanDirectoryOnce:
    """测试scan_directory_once函数的核心逻辑"""
    
    def test_scan_directory_once_new_file_creates_record(self, fs, mocker):
        """
        测试场景：扫描到新文件时应创建数据库记录
        
        当get_media_file_by_inode_device返回None（文件不存在于数据库）时，
        应该调用create_media_file创建新记录。
        """
        # 设置虚拟文件系统
        source_dir = Path("/test/source")
        fs.create_dir(source_dir)
        test_video = source_dir / "test_movie.mp4"
        fs.create_file(test_video, contents="fake video content")
        
        # 模拟CRUD函数
        mock_get_media_file = mocker.patch('app.crud.get_media_file_by_inode_device')
        mock_create_media_file = mocker.patch('app.crud.create_media_file')
        
        # 模拟文件不存在于数据库（返回None）
        mock_get_media_file.return_value = None
        
        # 模拟数据库会话
        mock_db_session = MagicMock()
        
        # 定义允许的扩展名
        allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov'}
        
        # 导入并调用待测试函数
        from ..scanner import scan_directory_once
        
        # 执行扫描
        scan_directory_once(mock_db_session, source_dir, allowed_extensions)
        
        # 验证CRUD函数调用
        mock_get_media_file.assert_called_once()
        mock_create_media_file.assert_called_once_with(mock_db_session, test_video)
    
    def test_scan_directory_once_existing_file_skips_creation(self, fs, mocker):
        """
        测试场景：文件已存在于数据库时应跳过创建
        
        当get_media_file_by_inode_device返回已存在的MediaFile对象时，
        不应该调用create_media_file。
        """
        # 设置虚拟文件系统
        source_dir = Path("/test/source")
        fs.create_dir(source_dir)
        test_video = source_dir / "existing_movie.mp4"
        fs.create_file(test_video, contents="fake video content")
        
        # 模拟CRUD函数
        mock_get_media_file = mocker.patch('app.crud.get_media_file_by_inode_device')
        mock_create_media_file = mocker.patch('app.crud.create_media_file')
        
        # 模拟文件已存在于数据库（返回MediaFile对象）
        mock_existing_media_file = MagicMock()
        mock_existing_media_file.id = 1
        mock_existing_media_file.original_filepath = str(test_video)
        mock_get_media_file.return_value = mock_existing_media_file
        
        # 模拟数据库会话
        mock_db_session = MagicMock()
        
        # 定义允许的扩展名
        allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov'}
        
        # 导入并调用待测试函数
        from ..scanner import scan_directory_once
        
        # 执行扫描
        scan_directory_once(mock_db_session, source_dir, allowed_extensions)
        
        # 验证CRUD函数调用
        mock_get_media_file.assert_called_once()
        mock_create_media_file.assert_not_called()  # 不应该创建新记录
    
    def test_scan_directory_once_ignores_non_video_files(self, fs, mocker):
        """
        测试场景：非视频文件应被忽略
        
        对于不在allowed_extensions中的文件，
        不应该调用任何CRUD函数。
        """
        # 设置虚拟文件系统
        source_dir = Path("/test/source")
        fs.create_dir(source_dir)
        
        # 创建非视频文件
        text_file = source_dir / "readme.txt"
        image_file = source_dir / "poster.jpg"
        fs.create_file(text_file, contents="some text")
        fs.create_file(image_file, contents="fake image")
        
        # 模拟CRUD函数
        mock_get_media_file = mocker.patch('app.crud.get_media_file_by_inode_device')
        mock_create_media_file = mocker.patch('app.crud.create_media_file')
        
        # 模拟数据库会话
        mock_db_session = MagicMock()
        
        # 定义允许的扩展名（不包含.txt和.jpg）
        allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov'}
        
        # 导入并调用待测试函数
        from ..scanner import scan_directory_once
        
        # 执行扫描
        scan_directory_once(mock_db_session, source_dir, allowed_extensions)
        
        # 验证CRUD函数都没有被调用
        mock_get_media_file.assert_not_called()
        mock_create_media_file.assert_not_called()
    
    def test_scan_directory_once_handles_empty_directory(self, fs, mocker):
        """
        测试场景：空目录处理
        
        对于空目录，不应该调用任何CRUD函数。
        """
        # 设置虚拟文件系统 - 空目录
        source_dir = Path("/test/empty_source")
        fs.create_dir(source_dir)
        
        # 模拟CRUD函数
        mock_get_media_file = mocker.patch('app.crud.get_media_file_by_inode_device')
        mock_create_media_file = mocker.patch('app.crud.create_media_file')
        
        # 模拟数据库会话
        mock_db_session = MagicMock()
        
        # 定义允许的扩展名
        allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov'}
        
        # 导入并调用待测试函数
        from ..scanner import scan_directory_once
        
        # 执行扫描
        scan_directory_once(mock_db_session, source_dir, allowed_extensions)
        
        # 验证CRUD函数都没有被调用
        mock_get_media_file.assert_not_called()
        mock_create_media_file.assert_not_called()
    
    def test_scan_directory_once_handles_mixed_files(self, fs, mocker):
        """
        测试场景：混合文件类型处理
        
        目录中同时包含视频文件和非视频文件时，
        只对视频文件调用CRUD函数。
        """
        # 设置虚拟文件系统
        source_dir = Path("/test/mixed_source")
        fs.create_dir(source_dir)
        
        # 创建混合文件
        video_file = source_dir / "movie.mp4"
        text_file = source_dir / "subtitle.srt"
        another_video = source_dir / "episode.mkv"
        image_file = source_dir / "thumbnail.png"
        
        fs.create_file(video_file, contents="video content")
        fs.create_file(text_file, contents="subtitle content")
        fs.create_file(another_video, contents="another video")
        fs.create_file(image_file, contents="image content")
        
        # 模拟CRUD函数
        mock_get_media_file = mocker.patch('app.crud.get_media_file_by_inode_device')
        mock_create_media_file = mocker.patch('app.crud.create_media_file')
        
        # 模拟文件都不存在于数据库
        mock_get_media_file.return_value = None
        
        # 模拟数据库会话
        mock_db_session = MagicMock()
        
        # 定义允许的扩展名
        allowed_extensions = {'.mp4', '.mkv', '.avi', '.mov'}
        
        # 导入并调用待测试函数
        from ..scanner import scan_directory_once
        
        # 执行扫描
        scan_directory_once(mock_db_session, source_dir, allowed_extensions)
        
        # 验证CRUD函数调用次数
        # 应该为2个视频文件各调用一次get_media_file_by_inode_device
        assert mock_get_media_file.call_count == 2
        # 应该为2个视频文件各调用一次create_media_file
        assert mock_create_media_file.call_count == 2 