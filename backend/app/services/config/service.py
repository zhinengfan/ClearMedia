"""
配置服务模块

提供配置项的数据库CRUD操作，包括动态黑名单验证、事务安全和Pydantic验证。
支持动态配置管理，确保系统的健壮性和安全性。
"""

import json
from typing import Dict, Any, Set
from sqlmodel import Session, select
from pydantic import ValidationError

from ...core.models import ConfigItem


def get_config_blacklist() -> Set[str]:
    """
    获取动态配置黑名单
    
    Returns:
        Set[str]: 不可配置的配置项集合
    """
    try:
        # 在函数内部导入，避免循环依赖
        from ...config import get_settings
        
        settings = get_settings()
        return settings.get_config_blacklist()
        
    except Exception:
        # 如果获取失败，返回默认黑名单
        return {"DATABASE_URL", "ENABLE_TMDB", "ENABLE_LLM"}


class ConfigService:
    """配置服务类
    
    提供配置项的数据库操作，包括读取所有配置和安全更新配置。
    所有写入操作都受到动态黑名单保护和Pydantic验证。
    """
    
    @staticmethod
    def read_all_from_db(db: Session) -> Dict[str, Any]:
        """从数据库读取所有配置项（薄封装）。

        该方法现在复用 ``core.utils.config_loader.load_config_from_session`` 
        以避免与 ``app.config._db_source`` 的逻辑重复。

        Args:
            db: 数据库会话

        Returns:
            Dict[str, Any]: 配置项键值对；读取失败时返回空字典。
        """
        try:
            from ...core.utils.config_loader import load_config_from_session  # 局部导入避免循环依赖

            return load_config_from_session(db)
        except Exception:
            # 如出现异常，保证返回空字典，防止调用方因 None 报错
            return {}
    
    @staticmethod
    def update_configs(db: Session, updates: Dict[str, Any]) -> None:
        """更新配置项到数据库
        
        此方法会：
        1. 过滤：只处理不在动态黑名单中的配置项
        2. 验证：使用Pydantic验证配置的有效性
        3. 事务：在事务内执行，失败时回滚
        
        Args:
            db: 数据库会话
            updates: 要更新的配置字典
            
        Raises:
            ValidationError: 当配置验证失败时
            Exception: 当数据库操作失败时
        """
        # 获取当前黑名单
        blacklist = get_config_blacklist()
        
        # 第一步：过滤 - 只保留不在黑名单中的配置项
        filtered_updates = {
            key: value for key, value in updates.items() 
            if key not in blacklist
        }
        
        # 如果没有可更新的配置项，直接返回
        if not filtered_updates:
            return
        
        try:
            # 第二步：验证 - 获取当前配置并与更新合并，进行Pydantic验证
            # 使用 Settings 内存快照作为当前配置，避免重复查询数据库
            from ...config import get_settings

            current_config = get_settings().model_dump()
            merged_config = {**current_config, **filtered_updates}
            
            # 创建临时Settings对象进行验证
            # 这将触发所有field_validator，确保配置的有效性
            from ...config import Settings
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