"""配置模块测试用例"""

import os
from pathlib import Path

import importlib

import pytest
from pydantic import ValidationError


def test_settings_from_env(test_config_env):
    """测试用例 1.1: 成功加载配置（环境变量隔离）

    Given: 一组完整且有效的环境变量
    When: Settings 类被实例化
    Then: 配置字段与环境变量保持一致
    """

    from app import config as cfg

    # 重新加载配置模块，确保读取最新环境变量
    importlib.reload(cfg)

    settings = cfg.Settings()

    # 基础配置
    assert settings.DATABASE_URL.endswith("/test.db")
    assert settings.SQLITE_ECHO is False

    # API 配置
    assert settings.OPENAI_API_KEY == "sk-test-key"
    assert settings.OPENAI_MODEL == "gpt-4-turbo-preview"
    assert settings.TMDB_API_KEY == "tmdb-test-key"

    # 目录配置
    assert settings.SOURCE_DIR == test_config_env["source_dir"].resolve()
    assert settings.TARGET_DIR == test_config_env["target_dir"].resolve()
    assert settings.SCAN_INTERVAL_SECONDS == 60

    # 环境配置
    assert settings.LOG_LEVEL == cfg.LogLevel.DEBUG
    assert settings.APP_ENV == cfg.AppEnv.DEV


def test_missing_required_env_vars(temp_env_file):
    """测试用例 1.2: 缺少环境变量
    
    Given: 一个缺少了TMDB_API_KEY等必需变量的.env文件
    When: Settings类被实例化
    Then: 程序应抛出pydantic_settings的验证错误 (Validation Error)
    """
    from app import config as cfg

    importlib.reload(cfg)

    # 创建一个缺少必需变量的.env文件
    env_content = """
    # 数据库配置
    DATABASE_URL=sqlite:///test.db
    SQLITE_ECHO=false
    
    # OpenAI配置 (缺少 OPENAI_API_KEY)
    OPENAI_API_BASE=https://api.openai.com/v1
    OPENAI_MODEL=gpt-4-turbo-preview
    
    # TMDB配置 (缺少 TMDB_API_KEY)
    TMDB_LANGUAGE=zh-CN
    TMDB_CONCURRENCY=5
    
    # 目录配置
    SOURCE_DIR={source_dir}
    TARGET_DIR={target_dir}
    SCAN_INTERVAL_SECONDS=60
    
    # 运行环境
    LOG_LEVEL=DEBUG
    APP_ENV=development
    """.format(
        source_dir=temp_env_file["source_dir"],
        target_dir=temp_env_file["target_dir"]
    )
    
    # 备份原始.env文件
    original_content = temp_env_file["env_file"].read_text()
    
    try:
        # 写入新的.env文件
        temp_env_file["env_file"].write_text(env_content)
        
        # 清除可能存在的环境变量
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        if "TMDB_API_KEY" in os.environ:
            del os.environ["TMDB_API_KEY"]
        
        # 验证是否抛出正确的异常
        with pytest.raises(ValidationError) as exc_info:
            cfg.Settings()
        
        # 验证错误消息
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg and "Field required" in error_msg
        assert "TMDB_API_KEY" in error_msg and "Field required" in error_msg
        
    finally:
        # 恢复原始.env文件
        temp_env_file["env_file"].write_text(original_content)


def test_settings_from_env_vars(env_vars):
    """测试从环境变量加载配置"""
    from app import config as cfg

    # 确保重新加载配置模块，以便使用temp_env_file所创建的.env
    importlib.reload(cfg)
    settings = cfg.Settings()
    assert settings.OPENAI_API_KEY == env_vars["OPENAI_API_KEY"]
    assert settings.TMDB_API_KEY == env_vars["TMDB_API_KEY"]


def test_settings_validation():
    """测试配置验证"""
    import tempfile
    from app import config as cfg

    # 准备临时目录和必需环境变量，避免 reload(cfg) 时抛出验证错误
    temp_dir = Path(tempfile.mkdtemp())
    source_dir = temp_dir / "source"
    target_dir = temp_dir / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["TMDB_API_KEY"] = "tmdb-test"
    os.environ["SOURCE_DIR"] = str(source_dir)
    os.environ["TARGET_DIR"] = str(target_dir)

    importlib.reload(cfg)

    minimal_config = dict(
        OPENAI_API_KEY="sk-test",
        TMDB_API_KEY="tmdb-test",
        SOURCE_DIR=source_dir,
        TARGET_DIR=target_dir,
    )

    # 测试无效的数据库URL
    with pytest.raises(ValidationError) as exc_info:
        cfg.Settings(**minimal_config, DATABASE_URL="mysql://localhost/db")
    assert "仅支持SQLite数据库" in str(exc_info.value)
    
    # 测试无效的TMDB语言代码
    with pytest.raises(ValidationError) as exc_info:
        cfg.Settings(**minimal_config, TMDB_LANGUAGE="invalid!")
    assert "无效的语言代码格式" in str(exc_info.value)

    # 清理环境变量
    for var in ["OPENAI_API_KEY", "TMDB_API_KEY", "SOURCE_DIR", "TARGET_DIR"]:
        os.environ.pop(var, None)


def test_directory_validation(temp_env_file):
    """测试目录验证器"""
    # 测试自动创建不存在的目录
    from app import config as cfg

    importlib.reload(cfg)
    new_dir = temp_env_file["temp_dir"] / "new_dir"
    settings = cfg.Settings(SOURCE_DIR=new_dir)
    assert new_dir.exists()
    assert settings.SOURCE_DIR == new_dir.resolve()
    
    # 测试目录权限检查
    if os.name != "nt":  # 跳过Windows
        no_access_dir = temp_env_file["temp_dir"] / "no_access"
        no_access_dir.mkdir(mode=0o000)
        with pytest.raises(ValidationError) as exc_info:
            cfg.Settings(SOURCE_DIR=no_access_dir)
        assert "缺少读写权限" in str(exc_info.value)


def test_settings_hot_reload(temp_env_file):
    """测试配置热重载"""
    # 初始配置
    from app import config as cfg

    importlib.reload(cfg)
    settings = cfg.get_settings()
    assert settings.OPENAI_API_KEY == "sk-test-key"
    
    # 修改.env文件
    env_content = temp_env_file["env_file"].read_text()
    new_content = env_content.replace(
        "OPENAI_API_KEY=sk-test-key",
        "OPENAI_API_KEY=sk-new-key"
    )
    temp_env_file["env_file"].write_text(new_content)

    # 重新加载模块以触发重新读取.env文件
    importlib.reload(cfg)
    
    # 获取新配置
    new_settings = cfg.get_settings()
    assert new_settings.OPENAI_API_KEY == "sk-new-key"


def test_singleton(env_vars):
    """测试配置单例模式"""
    from app import config as cfg

    # 确保必需环境变量已存在 (env_vars fixture 设置)
    importlib.reload(cfg)

    settings1 = cfg.get_settings()
    settings2 = cfg.get_settings()
    assert settings1 is settings2  # 验证是同一个对象 