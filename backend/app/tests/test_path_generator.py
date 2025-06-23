"""
path_generator.py 单元测试

测试路径生成逻辑的各种场景：电影、电视剧、带/不带年份等
"""

from pathlib import Path

from app.services.media.path_generator import generate_new_path, sanitize_title


class TestSanitizeTitle:
    """测试标题清理函数"""
    
    def test_normal_title(self):
        """测试正常标题"""
        result = sanitize_title("Inception")
        assert result == "Inception"
    
    def test_title_with_special_chars(self):
        """测试包含特殊字符的标题"""
        result = sanitize_title("Movie: The Beginning (2023) [HD]")
        assert result == "Movie The Beginning 2023 HD"
    
    def test_title_with_spaces_and_dashes(self):
        """测试包含空格和连字符的标题"""
        result = sanitize_title("Spider-Man: No Way Home")
        assert result == "Spider-Man No Way Home"
    
    def test_empty_title(self):
        """测试空标题"""
        result = sanitize_title("")
        assert result == ""
    
    def test_title_with_only_special_chars(self):
        """测试只包含特殊字符的标题"""
        result = sanitize_title("!@#$%^&*()")
        assert result == ""


class TestGenerateNewPath:
    """测试路径生成函数"""
    
    def test_movie_with_year(self):
        """测试电影路径生成（包含年份）"""
        media_info = {
            "title": "Inception",
            "release_date": "2010-07-16"
        }
        llm_guess = {"title": "Inception", "year": 2010, "type": "movie"}
        original_filepath = "/source/Inception.2010.1080p.BluRay.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/Movies/Inception (2010).mkv")
        assert result == expected
    
    def test_movie_without_year(self):
        """测试电影路径生成（不包含年份）"""
        media_info = {
            "title": "Unknown Movie"
        }
        llm_guess = {"title": "Unknown Movie", "type": "movie"}
        original_filepath = "/source/unknown.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/Movies/Unknown Movie.mkv")
        assert result == expected
    
    def test_tv_show_with_episode(self):
        """测试电视剧路径生成（包含季和集）"""
        media_info = {
            "name": "Breaking Bad",
            "first_air_date": "2008-01-20"
        }
        llm_guess = {
            "title": "Breaking Bad",
            "season": 1,
            "episode": 1,
            "type": "tv"
        }
        original_filepath = "/source/Breaking.Bad.S01E01.720p.WEB-DL.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/TV Shows/Breaking Bad (2008)/Breaking Bad S01E01.mkv")
        assert result == expected
    
    def test_tv_show_without_episode(self):
        """测试电视剧路径生成（不包含集数）"""
        media_info = {
            "name": "Game of Thrones",
            "first_air_date": "2011-04-17"
        }
        llm_guess = {
            "title": "Game of Thrones",
            "season": 1,
            "type": "tv"
        }
        original_filepath = "/source/game.of.thrones.s01.720p.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/TV Shows/Game of Thrones (2011)/Game of Thrones (2011).mkv")
        assert result == expected
    
    def test_tv_show_without_year(self):
        """测试电视剧路径生成（不包含年份）"""
        media_info = {
            "name": "Some TV Show"
        }
        llm_guess = {
            "title": "Some TV Show",
            "season": 2,
            "episode": 5,
            "type": "tv"
        }
        original_filepath = "/source/show.s02e05.mp4"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/TV Shows/Some TV Show/Some TV Show S02E05.mp4")
        assert result == expected
    
    def test_title_with_special_characters(self):
        """测试包含特殊字符的标题"""
        media_info = {
            "title": "Spider-Man: No Way Home",
            "release_date": "2021-12-17"
        }
        llm_guess = {"title": "Spider-Man: No Way Home", "year": 2021, "type": "movie"}
        original_filepath = "/source/Spider-Man.No.Way.Home.2021.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/Movies/Spider-Man No Way Home (2021).mkv")
        assert result == expected
    
    def test_no_llm_guess(self):
        """测试没有LLM猜测结果的情况"""
        media_info = {
            "name": "Some Show",
            "first_air_date": "2020-01-01"
        }
        llm_guess = None
        original_filepath = "/source/show.mkv"
        target_dir = Path("/target")
        
        result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
        expected = Path("/target/TV Shows/Some Show (2020)/Some Show (2020).mkv")
        assert result == expected
    
    def test_different_file_extensions(self):
        """测试不同的文件扩展名"""
        media_info = {
            "title": "Test Movie",
            "release_date": "2023-01-01"
        }
        llm_guess = {"title": "Test Movie", "year": 2023, "type": "movie"}
        
        # 测试不同扩展名
        for ext in [".mp4", ".avi", ".mov", ".wmv"]:
            original_filepath = f"/source/test{ext}"
            target_dir = Path("/target")
            
            result = generate_new_path(media_info, llm_guess, original_filepath, target_dir)
            expected = Path(f"/target/Movies/Test Movie (2023){ext}")
            assert result == expected 