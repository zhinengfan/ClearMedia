"""测试视频扩展名解析功能"""

from app.services.media.scanner import _parse_video_extensions


class TestParseVideoExtensions:
    """测试 _parse_video_extensions 函数"""
    
    def test_parse_single_extension(self):
        """测试解析单个扩展名"""
        result = _parse_video_extensions("mp4")
        assert result == {".mp4"}
    
    def test_parse_multiple_extensions(self):
        """测试解析多个扩展名（逗号分隔）"""
        result = _parse_video_extensions("mp4,mkv,avi")
        assert result == {".mp4", ".mkv", ".avi"}
    
    def test_parse_with_whitespace(self):
        """测试解析包含空格的扩展名"""
        result = _parse_video_extensions(" mp4 , mkv , avi ")
        assert result == {".mp4", ".mkv", ".avi"}
    
    def test_parse_with_dots(self):
        """测试解析已包含点的扩展名"""
        result = _parse_video_extensions(".mp4,.mkv")
        assert result == {".mp4", ".mkv"}
    
    def test_parse_mixed_case(self):
        """测试解析大小写混合的扩展名"""
        result = _parse_video_extensions("MP4,Mkv,AVI")
        assert result == {".mp4", ".mkv", ".avi"}
    
    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = _parse_video_extensions("")
        assert result == set()
    
    def test_parse_duplicate_extensions(self):
        """测试去重功能"""
        result = _parse_video_extensions("mp4,MP4,mp4")
        assert result == {".mp4"}
    
    def test_parse_with_empty_parts(self):
        """测试包含空白部分的字符串"""
        result = _parse_video_extensions("mp4,,mkv, ,avi")
        assert result == {".mp4", ".mkv", ".avi"} 