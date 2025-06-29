"""
配置管理API路由模块

提供动态配置管理的REST API端点，包括配置查询和更新功能。
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session
from loguru import logger

from ...db import get_db
from ...config import get_settings
from ...services.config import ConfigService, get_config_blacklist
from ...core.schemas import ConfigGetResponse, ConfigUpdateResponse


config_router = APIRouter(prefix="/api", tags=["config"])



@config_router.get("/config", response_model=ConfigGetResponse)
def get_config(db: Session = Depends(get_db)) -> ConfigGetResponse:
    """
    获取当前配置信息
    
    返回当前系统的所有配置项，敏感字段（如API密钥）会进行脱敏处理。
    同时返回配置黑名单列表。
    
    Args:
        db: 数据库会话依赖
        
    Returns:
        ConfigGetResponse: 包含所有配置项的响应对象，敏感字段已脱敏
    """
    try:
        # 获取当前设置
        settings = get_settings()
        
        # 转换为字典
        config_dict = settings.model_dump()
        
        # 获取配置黑名单列表
        blacklist = get_config_blacklist()
        
        # 返回 Pydantic 响应模型
        return ConfigGetResponse(
            config=config_dict,
            blacklist_keys=sorted(blacklist),
            message="配置获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取配置时发生错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取配置失败: {str(e)}"
        )


@config_router.post("/config", response_model=ConfigUpdateResponse)
def update_config(
    config_updates: Dict[str, Any] = Body(..., description="要更新的配置项字典"),
    db: Session = Depends(get_db)
) -> ConfigUpdateResponse:
    """
    更新配置项
    
    接收配置更新请求，仅允许更新不在黑名单中的配置项。
    更新成功后会触发配置热重载。
    
    Args:
        config_updates: 要更新的配置项字典
        db: 数据库会话依赖
        
    Returns:
        ConfigUpdateResponse: 更新结果信息，包含更新后的配置
        
    Raises:
        HTTPException: 当配置验证失败或更新失败时
    """
    try:
        # 验证输入
        if not config_updates:
            raise HTTPException(
                status_code=400,
                detail="配置更新数据不能为空"
            )
        
        # 获取当前黑名单
        blacklist = get_config_blacklist()
        
        # 过滤出可写的配置项（不在黑名单中）
        writable_updates = {
            key: value for key, value in config_updates.items()
            if key not in blacklist
        }
        
        # 记录被拒绝的配置项（在黑名单中）
        rejected_keys = [
            key for key in config_updates.keys()
            if key in blacklist
        ]
        
        # 检查是否有可更新的配置项
        if not writable_updates:
            return ConfigUpdateResponse(
                message="没有可更新的配置项",
                config={},  # 空配置，因为没有更新
                blacklist_keys=sorted(blacklist),
                rejected_keys=rejected_keys
            )
        
        logger.info(f"准备更新配置项: {list(writable_updates.keys())}")
        if rejected_keys:
            logger.warning(f"以下配置项在黑名单中，已拒绝更新: {rejected_keys}")
        
        # 调用配置服务更新配置
        ConfigService.update_configs(db, writable_updates)
        
        # 触发配置热重载
        updated_settings = get_settings(force_reload=True)
        
        # 🔧 应用配置副作用（如果在FastAPI应用上下文中）
        try:
            # 导入副作用处理函数
            import asyncio
            from ...main import _apply_settings_side_effects
            
            # 在新的事件循环中运行副作用处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_apply_settings_side_effects(updated_settings))
            finally:
                loop.close()
                
            logger.info("配置副作用处理完成")
        except Exception as e:
            logger.warning(f"配置副作用处理失败，但配置更新成功: {e}")
        
        # 返回更新结果
        updated_config = updated_settings.model_dump()
        
        return ConfigUpdateResponse(
            message="配置更新成功",
            config=updated_config,
            blacklist_keys=sorted(blacklist),
            updated_keys=list(writable_updates.keys()),
            rejected_keys=rejected_keys
        )
        
    except ValueError as e:
        # Pydantic 验证错误
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"配置验证失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"更新配置时发生错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"更新配置失败: {str(e)}"
        ) 