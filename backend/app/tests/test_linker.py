"""文件链接器 (linker.py) 的单元测试

使用 pyfakefs 模拟文件系统，验证硬链接创建函数在不同场景下的行为。
"""
import errno
import os
from pathlib import Path


from pyfakefs.fake_filesystem_unittest import TestCase
from unittest.mock import patch

# 导入待测试模块
from app.core.linker import create_hardlink, LinkResult


class TestCreateHardlink(TestCase):
    """测试 create_hardlink 函数的各种场景"""

    def setUp(self):
        """设置 pyfakefs"""
        self.setUpPyfakefs()

    def test_create_hardlink_success(self):
        """
        测试用例 1: 成功创建硬链接
        Given: 源文件和目标目录在同一个模拟设备上
        When: 调用创建硬链接的函数
        Then: 目标路径下出现了一个新的硬链接文件，并且该函数返回成功状态
        """
        # 设置测试数据
        source_path = Path("/source_dir/test_movie.mkv")
        destination_path = Path("/target_dir/movies/Test Movie (2023).mkv")
        
        # 在 pyfakefs 文件系统中创建源文件
        self.fs.create_file(source_path, contents="fake movie content")
        
        # 调用被测函数
        result = create_hardlink(source_path, destination_path)
        
        # 验证结果
        assert result == LinkResult.LINK_SUCCESS
        assert destination_path.exists()
        assert destination_path.is_file()
        # 验证是硬链接（相同的 inode）
        assert source_path.stat().st_ino == destination_path.stat().st_ino

    def test_create_hardlink_destination_exists_conflict(self):
        """
        测试用例 2: 目标路径已存在冲突
        Given: 目标路径下已经存在一个同名文件
        When: 调用创建硬链接的函数
        Then: 函数返回一个 CONFLICT 状态，且不覆盖现有文件，并且 os.link 未被调用
        """
        # 设置测试数据
        source_path = Path("/source_dir/test_movie.mkv")
        destination_path = Path("/target_dir/movies/Test Movie (2023).mkv")
        
        # 在 pyfakefs 文件系统中创建源文件和目标文件（冲突）
        self.fs.create_file(source_path, contents="fake movie content")
        self.fs.create_file(destination_path, contents="existing file")
        
        # 记录原始目标文件内容
        original_content = destination_path.read_text()
        
        # 监控 os.link 调用
        with patch("os.link") as mock_link:
            result = create_hardlink(source_path, destination_path)
        
        # 验证结果
        assert result == LinkResult.LINK_FAILED_CONFLICT
        # 验证原文件未被修改
        assert destination_path.read_text() == original_content
        # os.link 不应被调用
        mock_link.assert_not_called()

    def test_create_hardlink_cross_device_failure(self):
        """
        测试用例 3: 跨设备链接失败
        Given: 源文件和目标文件在不同的文件系统/设备上
        When: 调用创建硬链接的函数
        Then: 函数能捕获跨设备错误，并返回相应状态
        """
        # 设置测试数据
        source_path = Path("/source_dir/test_movie.mkv")
        destination_path = Path("/target_dir/movies/Test Movie (2023).mkv")
        
        # 在 pyfakefs 文件系统中创建源文件
        self.fs.create_file(source_path, contents="fake movie content")
        
        # 模拟跨设备错误：直接 patch os.link 抛出 EXDEV 错误
        cross_device_error = OSError(errno.EXDEV, "Invalid cross-device link")
        with patch("os.link", side_effect=cross_device_error):
            result = create_hardlink(source_path, destination_path)
        
        # 验证结果
        assert result == LinkResult.LINK_FAILED_CROSS_DEVICE

    def test_create_hardlink_source_not_exists(self):
        """
        测试用例 4: 源文件不存在
        Given: 源文件路径不存在
        When: 调用创建硬链接的函数
        Then: 函数返回 LINK_FAILED_NO_SOURCE 状态
        """
        # 设置测试数据
        source_path = Path("/source_dir/nonexistent.mkv")
        destination_path = Path("/target_dir/movies/Test Movie (2023).mkv")
        
        # 不创建源文件，保持其不存在状态
        
        # 调用被测函数
        result = create_hardlink(source_path, destination_path)
        
        # 验证结果
        assert result == LinkResult.LINK_FAILED_NO_SOURCE

    def test_create_hardlink_permission_denied(self):
        """
        测试用例 5: 权限拒绝错误
        Given: 目标目录没有写权限
        When: 调用创建硬链接的函数
        Then: 函数返回 LINK_FAILED_UNKNOWN 状态
        """
        # 设置测试数据
        source_path = Path("/source_dir/test_movie.mkv")
        destination_path = Path("/readonly_dir/movies/Test Movie (2023).mkv")
        
        # 在 pyfakefs 文件系统中创建源文件
        self.fs.create_file(source_path, contents="fake movie content")
        
        # 创建只读目录
        self.fs.create_dir("/readonly_dir/movies")
        # 设置目录为只读
        os.chmod("/readonly_dir/movies", 0o444)
        
        # 调用被测函数
        result = create_hardlink(source_path, destination_path)
        
        # 验证结果
        assert result == LinkResult.LINK_FAILED_UNKNOWN 