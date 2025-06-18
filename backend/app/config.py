from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """日志级别枚举"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppEnv(str, Enum):
    """应用运行环境枚举"""
    DEV = "development"
    PROD = "production"


class Settings(BaseSettings):
    """项目全局配置。

    所有字段均可通过环境变量或 `.env` 文件注入。
    在 FastAPI、背景任务等模块中，直接 `from app.config import settings` 获取单例。
    """

    # —— 数据库 ——
    DATABASE_URL: str = "sqlite:///clearmedia.db"
    SQLITE_ECHO: bool = False

    # —— OpenAI / LLM ——
    OPENAI_API_KEY: str = Field(..., description="OpenAI API密钥")
    OPENAI_API_BASE: str = Field(
        "https://api.openai.com/v1",
        description="OpenAI API基础URL，可选用代理"
    )
    OPENAI_MODEL: str = Field(
        "gpt-4-turbo-preview",
        description="OpenAI模型名称"
    )

    # —— TMDB ——
    TMDB_API_KEY: str = Field(..., description="TMDB API密钥")
    TMDB_LANGUAGE: str = Field(
        "zh-CN",
        description="TMDB API返回语言，可选: zh-CN, en-US, ko-KR等"
    )
    TMDB_CONCURRENCY: int = Field(
        10,
        description="TMDB API并发限制，与core/tmdb.py中的TMDB_SEMAPHORE保持一致",
        ge=1,
        le=20
    )

    # —— 扫描与并发 ——
    SOURCE_DIR: Path = Field(..., description="待扫描的源文件夹路径")
    TARGET_DIR: Path = Field(..., description="整理后的目标文件夹路径")
    SCAN_INTERVAL_SECONDS: int = Field(
        300,
        description="扫描间隔（秒）",
        ge=60,  # 最小1分钟
        le=3600  # 最大1小时
    )
    VIDEO_EXTENSIONS: str = Field(
        default=".mp4,.mkv,.avi,.mov,.wmv,.flv,.webm,.m4v",
        description="允许处理的媒体文件扩展名，逗号分隔格式"
    )

    # —— 运行环境 & 日志 ——
    LOG_LEVEL: LogLevel = Field(
        LogLevel.INFO,
        description="日志级别"
    )
    APP_ENV: AppEnv = Field(
        AppEnv.DEV,
        description="运行环境: development/production"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",  # 不统一前缀，保持与.env变量一致
        case_sensitive=True,
        validate_default=True,
    )

    # —— 验证器 ——
    @field_validator("SOURCE_DIR", "TARGET_DIR")
    @classmethod
    def validate_directory(cls, v: Path) -> Path:
        """验证目录是否存在且可访问"""
        if not v.exists():
            try:
                v.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"无法创建目录 {v}: {e}")
        if not os.access(v, os.R_OK | os.W_OK):
            raise ValueError(f"目录 {v} 缺少读写权限")
        return v.resolve()  # 返回绝对路径

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """验证SQLite数据库URL格式"""
        if not v.startswith("sqlite:///"):
            raise ValueError("仅支持SQLite数据库，URL必须以'sqlite:///'开头")
        return v

    @field_validator("TMDB_LANGUAGE")
    @classmethod
    def validate_tmdb_language(cls, v: str) -> str:
        """验证TMDB语言代码格式"""
        if not v.replace("-", "").isalnum():
            raise ValueError("无效的语言代码格式")
        return v

    @field_validator("VIDEO_EXTENSIONS")
    @classmethod
    def validate_video_extensions(cls, v: str) -> str:
        """验证视频扩展名格式"""
        if not v:
            raise ValueError("视频扩展名不能为空")
        
        # 分割扩展名
        extensions = [ext.strip() for ext in v.split(',') if ext.strip()]
        
        if not extensions:
            raise ValueError("视频扩展名列表不能为空")
        
        validated_extensions = []
        for extension in extensions:
            if not extension.startswith('.'):
                raise ValueError(f"扩展名必须以'.'开头: {extension}")
            # 简化验证：只检查基本格式，允许字母、数字和常见字符
            ext_body = extension[1:]  # 去掉点号
            if not ext_body:
                raise ValueError(f"扩展名不能只有点号: {extension}")
            # 允许字母、数字、以及常见的视频格式字符（如m4v中的数字）
            if not all(c.isalnum() for c in ext_body):
                raise ValueError(f"扩展名只能包含字母和数字: {extension}")
            validated_extensions.append(extension.lower())
        
        return ','.join(validated_extensions)


# 全局单例
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置单例，支持热重载。

    Returns:
        Settings: 全局配置实例
    """
    global _settings

    # 首次加载或热重载
    if _settings is None:
        _settings = Settings()
    else:
        # 检查.env文件是否有变化并重载
        env_file = Path(".env")
        if env_file.exists():
            _settings.__init__()

    return _settings


# 初始化单例
settings = get_settings()

__all__ = [
    "Settings",
    "LogLevel",
    "AppEnv",
    "settings",
    "get_settings",
] 