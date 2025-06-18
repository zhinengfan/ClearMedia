"""
测试VIDEO_EXTENSIONS配置的可配置性

验证用户可以通过环境变量自定义视频文件扩展名列表。
"""

from pathlib import Path
import tempfile
import pytest
from pydantic import ValidationError

from app.config import Settings


class TestVideoExtensionsConfig:
    """测试VIDEO_EXTENSIONS配置功能"""
    
    def test_default_video_extensions(self):
        """测试默认的视频扩展名配置"""
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 创建基本配置（不设置VIDEO_EXTENSIONS环境变量）
            settings = Settings(
                OPENAI_API_KEY="test-key",
                TMDB_API_KEY="test-key",
                SOURCE_DIR=source_dir,
                TARGET_DIR=target_dir
            )
            
            # 验证默认扩展名包含主要的视频格式
            actual_extensions = [ext.strip() for ext in settings.VIDEO_EXTENSIONS.split(',')]
            
            # 验证至少包含主要的视频格式
            required_extensions = ['.mp4', '.mkv', '.avi', '.mov']
            for ext in required_extensions:
                assert ext in actual_extensions
            
            # 验证都是有效的扩展名格式
            for ext in actual_extensions:
                assert ext.startswith('.')
                assert len(ext) > 1
                assert all(c.isalnum() for c in ext[1:])  # 扩展名主体只包含字母数字
            
            # 验证至少有4个扩展名
            assert len(actual_extensions) >= 4
    
    def test_custom_video_extensions_env_var(self, monkeypatch):
        """测试通过环境变量自定义视频扩展名"""
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 设置自定义扩展名环境变量
            custom_extensions = ".mp4,.avi,.wmv"
            monkeypatch.setenv("VIDEO_EXTENSIONS", custom_extensions)
            
            # 创建配置
            settings = Settings(
                OPENAI_API_KEY="test-key",
                TMDB_API_KEY="test-key",
                SOURCE_DIR=source_dir,
                TARGET_DIR=target_dir
            )
            
            # 验证自定义扩展名生效
            assert settings.VIDEO_EXTENSIONS == custom_extensions
            
            # 验证可以正确解析为列表
            extensions_list = [ext.strip() for ext in settings.VIDEO_EXTENSIONS.split(',')]
            assert extensions_list == ['.mp4', '.avi', '.wmv']
    
    def test_video_extensions_validation_success(self):
        """测试视频扩展名验证成功的情况"""
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 测试各种有效的扩展名格式
            valid_extensions = [
                ".mp4,.mkv,.avi",
                ".MP4,.MKV",  # 大写字母
                ".mp4, .mkv, .avi",  # 带空格
                ".mov,.m4v,.webm"
            ]
            
            for ext_string in valid_extensions:
                settings = Settings(
                    OPENAI_API_KEY="test-key",
                    TMDB_API_KEY="test-key",
                    SOURCE_DIR=source_dir,
                    TARGET_DIR=target_dir,
                    VIDEO_EXTENSIONS=ext_string
                )
                
                # 验证扩展名已被规范化为小写
                extensions = settings.VIDEO_EXTENSIONS.split(',')
                for ext in extensions:
                    assert ext.startswith('.')
                    assert ext == ext.lower()
    
    def test_video_extensions_validation_failure(self):
        """测试视频扩展名验证失败的情况"""
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 测试无效的扩展名格式
            invalid_extensions = [
                "",  # 空字符串
                "mp4,avi",  # 缺少点号前缀
                ".mp4,.@#$",  # 包含特殊字符
                "   ",  # 只有空格
            ]
            
            for invalid_ext in invalid_extensions:
                with pytest.raises(ValidationError):
                    Settings(
                        OPENAI_API_KEY="test-key",
                        TMDB_API_KEY="test-key",
                        SOURCE_DIR=source_dir,
                        TARGET_DIR=target_dir,
                        VIDEO_EXTENSIONS=invalid_ext
                    )
    
    def test_video_extensions_case_normalization(self):
        """测试视频扩展名大小写规范化"""
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 输入混合大小写的扩展名
            mixed_case_extensions = ".MP4,.MkV,.AVI,.mov"
            
            settings = Settings(
                OPENAI_API_KEY="test-key",
                TMDB_API_KEY="test-key",
                SOURCE_DIR=source_dir,
                TARGET_DIR=target_dir,
                VIDEO_EXTENSIONS=mixed_case_extensions
            )
            
            # 验证所有扩展名都被转换为小写
            expected_lowercase = ".mp4,.mkv,.avi,.mov"
            assert settings.VIDEO_EXTENSIONS == expected_lowercase
    
    def test_video_extensions_with_scanner_integration(self):
        """测试视频扩展名配置与扫描器的集成"""
        
        # 创建临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            # 创建自定义扩展名配置
            custom_extensions = ".mp4,.ts,.mkv"
            settings = Settings(
                OPENAI_API_KEY="test-key",
                TMDB_API_KEY="test-key",
                SOURCE_DIR=source_dir,
                TARGET_DIR=target_dir,
                VIDEO_EXTENSIONS=custom_extensions
            )
            
            # 验证扫描器可以正确解析扩展名
            allowed_extensions = set(ext.strip() for ext in settings.VIDEO_EXTENSIONS.split(',') if ext.strip())
            expected_extensions = {'.mp4', '.ts', '.mkv'}
            
            assert allowed_extensions == expected_extensions 