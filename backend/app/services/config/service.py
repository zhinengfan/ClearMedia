"""
配置服务模块

提供配置项的数据库CRUD操作，包括白名单验证、事务安全和Pydantic验证。
支持动态配置管理，确保系统的健壮性和安全性。
"""

import json
from typing import Dict, Any
from sqlmodel import Session, select
from pydantic import ValidationError

from ...core.models import ConfigItem
from ...config import Settings


# 定义可写配置项白名单 - 排除敏感和基础设施配置
WRITABLE_CONFIG_KEYS = {
    # OpenAI/LLM配置
    "OPENAI_API_BASE",
    "OPENAI_MODEL",
    
    # TMDB配置
    "TMDB_LANGUAGE", 
    "TMDB_CONCURRENCY",
    
    # 扫描与并发配置
    "SCAN_INTERVAL_SECONDS",
    "SCAN_EXCLUDE_TARGET_DIR", 
    "SCAN_FOLLOW_SYMLINKS",
    "MIN_FILE_SIZE_MB",
    "VIDEO_EXTENSIONS",
    
    # 日志与环境配置
    "LOG_LEVEL",
    "APP_ENV",
    
    # 功能开关
    "ENABLE_TMDB",
    "ENABLE_LLM",
    
    # 队列与工作者
    "WORKER_COUNT",
    
    # CORS配置
    "CORS_ORIGINS",
}

# 明确排除的配置项（敏感或基础设施相关）
EXCLUDED_CONFIG_KEYS = {
    "DATABASE_URL",      # 数据库连接，防止循环依赖和连接丢失
    "OPENAI_API_KEY",    # API密钥，安全敏感
    "TMDB_API_KEY",      # API密钥，安全敏感
    "SOURCE_DIR",        # 文件系统路径，影响基础功能
    "TARGET_DIR",        # 文件系统路径，影响基础功能
    "SQLITE_ECHO",       # 数据库调试选项
}


class ConfigService:
    """配置服务类
    
    提供配置项的数据库操作，包括读取所有配置和安全更新配置。
    所有写入操作都受到白名单保护和Pydantic验证。
    """
    
    @staticmethod
    def read_all_from_db(db: Session) -> Dict[str, Any]:
        """从数据库读取所有配置项
        
        Args:
            db: 数据库会话
            
        Returns:
            包含所有配置项的字典，key为配置名，value为反序列化后的值。
            如果数据库为空或发生错误，返回空字典{}。
        """
        try:
            # 查询所有配置项
            statement = select(ConfigItem)
            config_items = db.exec(statement).all()
            
            # 构建配置字典
            config_dict = {}
            for item in config_items:
                try:
                    # JSON反序列化配置值
                    config_dict[item.key] = json.loads(item.value)
                except (json.JSONDecodeError, TypeError):
                    # 如果反序列化失败，跳过该配置项并记录警告
                    # 实际应用中可能需要日志记录
                    continue
                    
            return config_dict
            
        except Exception:
            # 如果发生任何数据库错误，返回空字典确保应用能正常启动
            return {}
    
    @staticmethod
    def update_configs(db: Session, updates: Dict[str, Any]) -> None:
        """更新配置项到数据库
        
        此方法会：
        1. 过滤：只处理白名单内的配置项
        2. 验证：使用Pydantic验证配置的有效性
        3. 事务：在事务内执行，失败时回滚
        
        Args:
            db: 数据库会话
            updates: 要更新的配置字典
            
        Raises:
            ValidationError: 当配置验证失败时
            Exception: 当数据库操作失败时
        """
        # 第一步：过滤 - 只保留白名单内的配置项
        filtered_updates = {
            key: value for key, value in updates.items() 
            if key in WRITABLE_CONFIG_KEYS
        }
        
        # 如果没有可更新的配置项，直接返回
        if not filtered_updates:
            return
        
        try:
            # 第二步：验证 - 获取当前配置并与更新合并，进行Pydantic验证
            current_config = ConfigService.read_all_from_db(db)
            merged_config = {**current_config, **filtered_updates}
            
            # 创建临时Settings对象进行验证
            # 这将触发所有field_validator，确保配置的有效性
            Settings(**merged_config)
            
            # 第三步：写入 - 验证通过后，将过滤后的更新写入数据库
            for key, value in filtered_updates.items():
                # 序列化配置值为JSON字符串
                json_value = json.dumps(value)
                
                # 查找现有配置项
                statement = select(ConfigItem).where(ConfigItem.key == key)
                existing_item = db.exec(statement).first()
                
                if existing_item:
                    # 更新现有配置项
                    existing_item.value = json_value
                    # updated_at会自动更新（由模型的sa_column_kwargs处理）
                    db.add(existing_item)
                else:
                    # 创建新配置项
                    new_item = ConfigItem(
                        key=key,
                        value=json_value,
                        description=f"动态配置项: {key}"
                    )
                    db.add(new_item)
            
            # 第四步：提交 - 提交更改
            db.commit()
            
        except ValidationError:
            # Pydantic验证失败，回滚更改
            db.rollback()
            raise
        except Exception:
            # 其他异常，回滚更改
            db.rollback()
            raise 