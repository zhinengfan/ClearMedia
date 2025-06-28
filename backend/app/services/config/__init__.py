"""配置服务包

提供配置项的数据库CRUD操作，包括动态黑名单验证、事务安全和Pydantic验证。
"""

from .service import ConfigService, get_config_blacklist

__all__ = ["ConfigService", "get_config_blacklist"] 