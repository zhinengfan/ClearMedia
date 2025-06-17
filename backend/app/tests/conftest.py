"""测试配置和共享fixture"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_env_file():
    """创建临时.env文件的fixture"""
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # 创建临时的源目录和目标目录
        source_dir = temp_dir_path / "source"
        target_dir = temp_dir_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建临时.env文件
        env_file = temp_dir_path / ".env"
        env_content = f"""
        # 数据库配置
        DATABASE_URL=sqlite:///{temp_dir_path}/test.db
        SQLITE_ECHO=false
        
        # OpenAI配置
        OPENAI_API_KEY=sk-test-key
        OPENAI_API_BASE=https://api.openai.com/v1
        OPENAI_MODEL=gpt-4-turbo-preview
        
        # TMDB配置
        TMDB_API_KEY=tmdb-test-key
        TMDB_LANGUAGE=zh-CN
        TMDB_CONCURRENCY=5
        
        # 目录配置
        SOURCE_DIR={source_dir}
        TARGET_DIR={target_dir}
        SCAN_INTERVAL_SECONDS=60
        
        # 运行环境
        LOG_LEVEL=DEBUG
        APP_ENV=development
        """
        env_file.write_text(env_content)
        
        # 切换到临时目录
        old_cwd = os.getcwd()
        os.chdir(temp_dir_path)
        
        yield {
            "env_file": env_file,
            "temp_dir": temp_dir_path,
            "source_dir": source_dir,
            "target_dir": target_dir,
        }
        
        # 测试结束后恢复工作目录
        os.chdir(old_cwd)


@pytest.fixture
def env_vars():
    """提供测试用的环境变量"""
    # 保存原始环境变量
    old_env = {}
    # 创建临时目录供SOURCE_DIR和TARGET_DIR
    temp_dir = Path(tempfile.mkdtemp())
    source_dir = temp_dir / "source"
    target_dir = temp_dir / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    test_vars = {
        "OPENAI_API_KEY": "sk-test-key-from-env",
        "TMDB_API_KEY": "tmdb-test-key-from-env",
        "SOURCE_DIR": str(source_dir),
        "TARGET_DIR": str(target_dir),
    }
    
    for k, v in test_vars.items():
        if k in os.environ:
            old_env[k] = os.environ[k]
        os.environ[k] = v
    
    yield test_vars
    
    # 恢复原始环境变量
    for k in test_vars:
        if k in old_env:
            os.environ[k] = old_env[k]
        else:
            del os.environ[k] 


@pytest.fixture
def mock_tmdbsimple():
    """提供模拟的tmdbsimple库"""
    # 创建一个模拟的Search类
    mock_search = MagicMock()
    
    # 创建一个模拟的Movies类
    mock_movies = MagicMock()
    
    # 创建一个模拟的tmdbsimple模块
    mock_tmdb = MagicMock()
    mock_tmdb.Search.return_value = mock_search
    mock_tmdb.Movies.return_value = mock_movies
    
    # 设置API_KEY属性
    mock_tmdb.API_KEY = None
    
    return {
        "tmdb": mock_tmdb,
        "search": mock_search,
        "movies": mock_movies
    } 