"""
FastAPI 查询参数验证依赖模块

提供统一的查询参数验证函数，对于不支持的参数值返回 HTTP 422 错误。
"""

from typing import Optional
from fastapi import HTTPException, Query
from ..core.models import FileStatus

# 定义允许的排序字段和方向
ALLOWED_SORT_FIELDS = ["created_at", "updated_at", "original_filename", "status"]
ALLOWED_SORT_DIRECTIONS = ["asc", "desc"]

# 定义所有有效的文件状态
VALID_STATUSES = [
    FileStatus.PENDING, 
    FileStatus.QUEUED, 
    FileStatus.PROCESSING, 
    FileStatus.COMPLETED,
    FileStatus.FAILED, 
    FileStatus.CONFLICT, 
    FileStatus.NO_MATCH
]


def validate_sort_parameter(sort: Optional[str] = Query(
    "created_at:desc",
    description="排序方式，格式为 'field:direction'。支持字段: created_at, updated_at, original_filename, status。支持方向: asc, desc"
)) -> Optional[str]:
    """
    验证排序参数格式和字段有效性
    
    Args:
        sort: 排序参数字符串，如 'created_at:desc'
        
    Returns:
        str: 验证通过的排序参数
        
    Raises:
        HTTPException: 当字段或方向不支持时抛出422错误
    """
    if not sort:
        return sort
    
    try:
        field, direction = sort.split(":", 1)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="排序参数格式错误。正确格式: 'field:direction'，如 'created_at:desc'"
        )
    
    # 验证字段
    if field not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的排序字段: {field}。支持的字段: {', '.join(ALLOWED_SORT_FIELDS)}"
        )
    
    # 验证方向
    if direction not in ALLOWED_SORT_DIRECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的排序方向: {direction}。支持的方向: {', '.join(ALLOWED_SORT_DIRECTIONS)}"
        )
    
    return sort


def validate_status_parameter(status: Optional[str] = Query(
    None,
    description=f"按状态筛选，支持多个状态用逗号分隔: {', '.join(VALID_STATUSES)}"
)) -> Optional[str]:
    """
    验证状态参数有效性
    
    Args:
        status: 状态参数字符串，如 'PENDING,COMPLETED' 或 'PENDING'
        
    Returns:
        Optional[str]: 验证通过的状态参数
        
    Raises:
        HTTPException: 当状态值无效时抛出422错误
    """
    if not status or not status.strip():
        return status
    
    # 分割逗号分隔的状态值，并去除空白
    statuses = [s.strip().upper() for s in status.split(',') if s.strip()]
    
    if not statuses:
        return status
    
    # 验证所有状态值
    invalid_statuses = [s for s in statuses if s not in VALID_STATUSES]
    if invalid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的状态值: {', '.join(invalid_statuses)}。支持的状态: {', '.join(VALID_STATUSES)}"
        )
    
    return status


class ValidatedQueryParams:
    """查询参数验证结果类"""
    
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="跳过的记录数"),
        limit: int = Query(20, ge=1, le=500, description="返回的记录数限制（最大500）"),
        status: Optional[str] = None,
        search: Optional[str] = Query(None, description="按文件名模糊搜索"),
        sort: Optional[str] = None
    ):
        self.skip = skip
        self.limit = limit
        self.status = status
        self.search = search
        self.sort = sort 