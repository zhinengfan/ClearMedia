"""ClearMedia API 聚合器包

此包负责聚合各 endpoints 子模块的路由，并向外暴露统一的 `router` 变量，
供 `main.py` 及测试用例 `from app.api import router` 使用。
"""

from fastapi import APIRouter

# 子路由导入应放在 FastAPI 创建之后以避免循环依赖
from .endpoints.media import media_router  # noqa: E402  pylint: disable=wrong-import-position
from .endpoints.config import config_router  # noqa: E402  pylint: disable=wrong-import-position

# 创建聚合路由器
router = APIRouter()
router.include_router(media_router)
router.include_router(config_router)

# OpenAPI 标签元数据，供 FastAPI 应用在生成文档时使用
tags_metadata = [
    {
        "name": "media",
        "description": "媒体文件相关接口：包含文件列表、详情、重试、统计与搜索建议等功能",
    },
    {
        "name": "config",
        "description": "系统动态配置管理接口：获取当前配置、更新配置并触发热重载",
    },
]

__all__ = ["router", "tags_metadata"]
