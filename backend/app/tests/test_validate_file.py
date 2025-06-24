"""测试文件校验功能"""

import tempfile
from pathlib import Path
from unittest.mock import patch
from app.services.media.scanner import _validate_file


class TestValidateFile:
    """测试 _validate_file 函数"""
    
    def test_validate_file_extension_valid(self):
        """测试有效扩展名的文件校验"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
            assert is_valid is True
            assert message == ""
    
    def test_validate_file_extension_invalid(self):
        """测试无效扩展名的文件校验"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp_file:
            file_path = Path(tmp_file.name)
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
            assert is_valid is False
            assert "扩展名" in message
    
    def test_validate_file_extension_case_insensitive(self):
        """测试扩展名大小写不敏感"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".MP4") as tmp_file:
            file_path = Path(tmp_file.name)
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
            assert is_valid is True
            assert message == ""
    
    def test_validate_file_size_valid(self):
        """测试文件大小校验通过"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建临时文件并写入数据
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            tmp_file.write(b"x" * 1024)  # 1KB
            tmp_file.flush()
            file_path = Path(tmp_file.name)
            
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=512)  # 最小512B
            assert is_valid is True
            assert message == ""
    
    def test_validate_file_size_too_small(self):
        """测试文件太小被拒绝"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建临时文件并写入少量数据
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            tmp_file.write(b"x" * 100)  # 100B
            tmp_file.flush()
            file_path = Path(tmp_file.name)
            
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=1024)  # 最小1KB
            assert is_valid is False
            assert "文件大小" in message
    
    def test_validate_file_size_zero_min_allowed(self):
        """测试最小大小为0时不检查大小"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        # 创建空文件
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
            assert is_valid is True
            assert message == ""
    
    def test_validate_file_not_exists(self):
        """测试文件不存在的情况"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        file_path = Path("/non/existent/file.mp4")
        
        is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
        assert is_valid is False
        assert "文件不存在" in message or "无法获取文件信息" in message
    
    def test_validate_file_stat_error(self):
        """测试获取文件信息失败的情况"""
        allowed_extensions = {".mp4", ".mkv", ".avi"}
        
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_file:
            file_path = Path(tmp_file.name)
            
            # 模拟 stat() 抛出异常
            with patch.object(Path, 'stat', side_effect=OSError("Permission denied")):
                is_valid, message = _validate_file(file_path, allowed_extensions, min_size_bytes=0)
                assert is_valid is False
                assert "无法获取文件信息" in message 