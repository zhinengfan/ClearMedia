from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from loguru import logger

# 导入相关模块以便进行全局副作用更新
import tmdbsimple
import asyncio


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


def _db_source(settings: BaseSettings) -> Dict[str, Any]:
    """
    从数据库读取配置的自定义源函数
    
    Args:
        settings: Settings实例
        
    Returns:
        包含数据库配置的字典
    """
    try:
        # 为避免循环依赖，直接查询数据库，不再通过 ConfigService
        from .db import get_session_factory
        from .core.models import ConfigItem
        from sqlmodel import select
        import json
        
        # 获取数据库会话
        session_factory = get_session_factory()
        with session_factory() as session:
            # 直接查询ConfigItem表，避免ConfigService导入引起的循环依赖
            config_items = session.exec(select(ConfigItem)).all()
            config_dict = {}
            for item in config_items:
                try:
                    config_dict[item.key] = json.loads(item.value)
                except Exception:
                    # 忽略反序列化错误
                    continue
            return config_dict
    except Exception as e:
        # 启动早期数据库可能尚未就绪或发生循环导入，此处仅记录调试日志，避免误导性的警告
        logger.debug(f"从数据库加载配置失败，使用默认配置: {e}")
        return {}


def _on_settings_reloaded(settings: "Settings") -> None:
    """
    配置重载钩子函数，处理配置更新后的全局副作用
    
    Args:
        settings: 重新加载后的Settings实例
    """
    try:
        # 更新 tmdbsimple API Key
        tmdbsimple.API_KEY = settings.TMDB_API_KEY
        logger.info("已更新 tmdbsimple.API_KEY")
        
        # 更新 tmdbsimple 语言设置
        if hasattr(tmdbsimple, 'DEFAULT_LANGUAGE'):
            tmdbsimple.DEFAULT_LANGUAGE = settings.TMDB_LANGUAGE
            logger.info(f"已更新 tmdbsimple.DEFAULT_LANGUAGE 为 {settings.TMDB_LANGUAGE}")
        
        # 重新创建 TMDB_SEMAPHORE（需要更新tmdb.py中的全局变量）
        # 注意：这里我们需要通知tmdb模块更新其SEMAPHORE
        try:
            from .core import tmdb
            # 重新创建信号量
            tmdb.TMDB_SEMAPHORE = asyncio.Semaphore(settings.TMDB_CONCURRENCY)
            logger.info(f"已更新 TMDB_SEMAPHORE 并发限制为 {settings.TMDB_CONCURRENCY}")
        except Exception as e:
            logger.warning(f"更新 TMDB_SEMAPHORE 失败: {e}")
        
        logger.info("配置重载钩子执行完成")
        
    except Exception as e:
        logger.error(f"执行配置重载钩子时出错: {e}")


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
        default=300,
        description="扫描器两次扫描之间的等待时间（秒）"
    )
    SCAN_EXCLUDE_TARGET_DIR: bool = Field(
        default=True,
        description="扫描时是否自动排除目标目录"
    )
    SCAN_FOLLOW_SYMLINKS: bool = Field(
        default=False,
        description="扫描时是否跟随符号链接（软链接），开启可能导致循环扫描"
    )
    MIN_FILE_SIZE_MB: int = Field(
        default=10,
        description="扫描时忽略小于此大小的文件（MB），0表示不限制"
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

    # —— 功能开关 ——
    ENABLE_TMDB: bool = Field(
        default=True,
        description="是否启用TMDB API调用"
    )
    ENABLE_LLM: bool = Field(
        default=True,
        description="是否启用LLM分析功能"
    )
    
    # —— 队列与工作者 ——
    WORKER_COUNT: int = Field(
        default=2,
        description="处理媒体文件的工作者协程数量",
        ge=1,
        le=10
    )

    # —— CORS 跨域配置 ——
    CORS_ORIGINS: str = Field(
        default="*",
        description="允许跨域访问的源地址，逗号分隔格式，如: http://localhost:3000,https://example.com"
    )

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        env_prefix="",  # 不统一前缀，保持与.env变量一致
        case_sensitive=True,
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        自定义配置源优先级：数据库 > 环境变量 > .env文件 > 默认值
        
        Returns:
            配置源的优先级元组，优先级从高到低
        """
        # 创建数据库配置源
        from pydantic_settings.sources import PydanticBaseSettingsSource
        
        class DatabaseSource(PydanticBaseSettingsSource):
            def get_field_value(self, field_info, field_name: str):
                # 调用数据库源函数获取配置
                db_config = _db_source(self.settings_cls)
                return db_config.get(field_name), field_name, False
            
            def prepare_field_value(self, field_name: str, field_info, value, value_from):
                return value
            
            def __call__(self):
                d = {}
                db_config = _db_source(self.settings_cls)
                for field_name in self.settings_cls.model_fields:
                    if field_name in db_config:
                        d[field_name] = db_config[field_name]
                return d
        
        return (
            init_settings,  # 程序初始化时的配置（最高优先级）
            DatabaseSource(settings_cls),  # 数据库配置源
            env_settings,   # 环境变量
            dotenv_settings,  # .env文件
            file_secret_settings,  # 文件密钥源
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

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """验证CORS源地址格式"""
        if not v:
            raise ValueError("CORS源地址不能为空")
        
        # 如果是通配符，直接返回
        if v.strip() == "*":
            return "*"
        
        # 分割源地址
        origins = [origin.strip() for origin in v.split(',') if origin.strip()]
        
        if not origins:
            raise ValueError("CORS源地址列表不能为空")
        
        validated_origins = []
        for origin in origins:
            # 基本URL格式验证
            if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
                raise ValueError(f"CORS源地址必须以http://或https://开头，或使用通配符*: {origin}")
            validated_origins.append(origin)
        
        return ','.join(validated_origins)

    def get_cors_origins_list(self) -> list[str]:
        """获取CORS_ORIGINS的列表形式"""
        return self.CORS_ORIGINS.split(',')


# 全局单例
_settings: Settings | None = None


def get_settings(force_reload: bool = False) -> Settings:
    """返回全局配置单例，如果不存在则创建。
    
    Args:
        force_reload: 是否强制重新加载配置
        
    Returns:
        Settings实例
    """
    global _settings
    if _settings is None or force_reload:
        _settings = Settings()
        # 立即调用配置重载钩子
        _on_settings_reloaded(_settings)
    return _settings


def cleanup_deprecated_configs() -> None:
    """
    清理数据库中已废弃的配置项
    
    此函数比较Settings模型字段与数据库中的配置键，
    删除数据库中存在但Settings模型中已不存在的配置项。
    """
    try:
        from .db import get_session_factory
        from .core.models import ConfigItem
        from sqlmodel import select
        
        # 获取Settings模型定义的所有字段名
        settings_fields = set(Settings.model_fields.keys())
        logger.info(f"Settings模型定义的字段: {settings_fields}")
        
        # 从数据库获取所有配置键
        session_factory = get_session_factory()
        with session_factory() as session:
            statement = select(ConfigItem.key)
            db_keys = set(session.exec(statement).all())
            logger.info(f"数据库中存在的配置键: {db_keys}")
            
            # 找出废弃的配置键（数据库中有但Settings模型中没有）
            deprecated_keys = db_keys - settings_fields
            
            if deprecated_keys:
                logger.warning(f"发现废弃的配置键: {deprecated_keys}")
                
                # 删除废弃的配置项
                for key in deprecated_keys:
                    statement = select(ConfigItem).where(ConfigItem.key == key)
                    item = session.exec(statement).first()
                    if item:
                        session.delete(item)
                        logger.warning(f"已删除废弃配置项: {key}")
                
                # 提交更改
                session.commit()
                logger.info(f"已清理 {len(deprecated_keys)} 个废弃配置项")
            else:
                logger.info("未发现废弃的配置项")
                
    except Exception as e:
        logger.error(f"清理废弃配置项时出错: {e}")


# 初始化单例
settings = get_settings()

__all__ = [
    "Settings",
    "LogLevel", 
    "AppEnv",
    "settings",
    "get_settings",
    "cleanup_deprecated_configs",
] 