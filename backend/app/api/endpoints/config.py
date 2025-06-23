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
from ...services.config_service import ConfigService, WRITABLE_CONFIG_KEYS


config_router = APIRouter(prefix="/api", tags=["config"])


def _mask_sensitive_fields(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    对敏感字段进行脱敏处理
    
    Args:
        config_dict: 原始配置字典
        
    Returns:
        脱敏后的配置字典
    """
    sensitive_fields = {
        "OPENAI_API_KEY",
        "TMDB_API_KEY",
        "DATABASE_URL"
    }
    
    masked_config = config_dict.copy()
    for field in sensitive_fields:
        if field in masked_config and masked_config[field]:
            value = str(masked_config[field])
            # 保留前3位和后3位，中间用***替换
            if len(value) > 6:
                masked_config[field] = value[:3] + "***" + value[-3:]
            else:
                masked_config[field] = "***"
    
    return masked_config


@config_router.get("/config")
def get_config(db: Session = Depends(get_db)):
    """
    获取当前配置信息
    
    返回当前系统的所有配置项，敏感字段（如API密钥）会进行脱敏处理。
    
    Args:
        db: 数据库会话依赖
        
    Returns:
        dict: 包含所有配置项的字典，敏感字段已脱敏
    """
    try:
        # 获取当前设置
        settings = get_settings()
        
        # 转换为字典
        config_dict = settings.model_dump()
        
        # 对敏感字段进行脱敏
        masked_config = _mask_sensitive_fields(config_dict)
        
        # 添加元数据信息
        return {
            "config": masked_config,
            "writable_keys": list(WRITABLE_CONFIG_KEYS),
            "message": "配置获取成功，敏感字段已脱敏"
        }
        
    except Exception as e:
        logger.error(f"获取配置时发生错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取配置失败: {str(e)}"
        )


@config_router.post("/config")
def update_config(
    config_updates: Dict[str, Any] = Body(..., description="要更新的配置项字典"),
    db: Session = Depends(get_db)
):
    """
    更新配置项
    
    接收配置更新请求，仅允许更新白名单内的配置项。
    更新成功后会触发配置热重载。
    
    Args:
        config_updates: 要更新的配置项字典
        db: 数据库会话依赖
        
    Returns:
        dict: 更新结果信息，包含更新后的配置
        
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
        
        # 过滤出可写的配置项
        writable_updates = {
            key: value for key, value in config_updates.items()
            if key in WRITABLE_CONFIG_KEYS
        }
        
        # 检查是否有可更新的配置项
        if not writable_updates:
            return {
                "message": "没有可更新的配置项",
                "writable_keys": list(WRITABLE_CONFIG_KEYS),
                "rejected_keys": list(config_updates.keys())
            }
        
        # 记录被拒绝的配置项
        rejected_keys = [
            key for key in config_updates.keys()
            if key not in WRITABLE_CONFIG_KEYS
        ]
        
        logger.info(f"准备更新配置项: {list(writable_updates.keys())}")
        if rejected_keys:
            logger.warning(f"以下配置项不在白名单中，已拒绝更新: {rejected_keys}")
        
        # 调用配置服务更新配置
        ConfigService.update_configs(db, writable_updates)
        
        # 触发配置热重载
        updated_settings = get_settings(force_reload=True)
        
        # 返回更新结果
        updated_config = _mask_sensitive_fields(updated_settings.model_dump())
        
        return {
            "message": "配置更新成功",
            "updated_keys": list(writable_updates.keys()),
            "rejected_keys": rejected_keys,
            "config": updated_config
        }
        
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