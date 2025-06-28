from __future__ import annotations

"""配置加载工具

该模块提供从给定 SQLModel Session 中批量加载配置项的通用函数，
避免在 config.py 与 ConfigService 之间出现重复实现。
"""

from typing import Any, Dict
import json
from loguru import logger
from sqlmodel import Session, select

from ..models import ConfigItem

__all__ = ["load_config_from_session"]


def load_config_from_session(session: Session) -> Dict[str, Any]:
    """从数据库会话批量读取配置项。

    Args:
        session: 已建立的 SQLModel Session。

    Returns:
        Dict[str, Any]: 键为配置项名称，值为反序列化后的 Python 对象。
    """
    try:
        statement = select(ConfigItem)
        items = session.exec(statement).all()

        config: Dict[str, Any] = {}
        invalid_items = []
        for item in items:
            try:
                config[item.key] = json.loads(item.value)
            except (json.JSONDecodeError, TypeError) as err:
                invalid_items.append(f"{item.key}: {err}")
                continue

        if invalid_items:
            logger.warning(f"从数据库读取配置时发现无效项: {invalid_items}")

        return config

    except Exception as exc:  # pragma: no cover – 记录并返回空 dict
        logger.warning(f"加载数据库配置失败，返回空配置: {exc}")
        return {} 