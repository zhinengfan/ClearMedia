"""
媒体文件API路由模块

提供ClearMedia的媒体文件相关REST API端点，包括媒体文件查询、统计等功能。
"""

from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, distinct
from loguru import logger
from pydantic import BaseModel

from ...db import get_db
from ...core.models import MediaFile, FileStatus
from ...core.schemas import (
    MediaFilesResponse,
    MediaFileDetail,
    SuggestionResponse,
    RetryResponse,
)
from ...crud import get_media_file_by_id, update_media_file_status
from ..deps import validate_sort_parameter, validate_status_parameter


# 定义可重试的文件状态常量（使用元组确保只读）
RETRYABLE_STATUSES = (FileStatus.FAILED, FileStatus.NO_MATCH, FileStatus.CONFLICT)

# 定义允许的排序字段和方向
ALLOWED_SORT_FIELDS = {
    "created_at": MediaFile.created_at,
    "updated_at": MediaFile.updated_at,
    "original_filename": MediaFile.original_filename,
    "status": MediaFile.status,
}

ALLOWED_SORT_DIRECTIONS = ["asc", "desc"]

# 定义所有有效的文件状态
VALID_STATUSES = [
    FileStatus.PENDING, FileStatus.QUEUED, FileStatus.PROCESSING, FileStatus.COMPLETED,
    FileStatus.FAILED, FileStatus.CONFLICT, FileStatus.NO_MATCH
]


media_router = APIRouter(prefix="/api", tags=["media"])


def parse_sort_parameter(sort_param: Optional[str]) -> tuple:
    """
    解析排序参数，格式为 'field:direction'
    
    Args:
        sort_param: 排序参数字符串，如 'created_at:desc'
        
    Returns:
        tuple: (field_column, is_descending) 或 (None, None) 如果为空
        
    注意: 此函数仅处理内部解析，参数验证由依赖函数 validate_sort_parameter 处理
    """
    if not sort_param:
        # 默认排序：按创建时间降序
        return MediaFile.created_at, True
    
    field, direction = sort_param.split(":", 1)
    return ALLOWED_SORT_FIELDS[field], direction == "desc"


def parse_status_parameter(status_param: Optional[str]) -> Optional[List[str]]:
    """
    解析状态参数，支持逗号分隔的多个状态
    
    Args:
        status_param: 状态参数字符串，如 'PENDING,COMPLETED' 或 'PENDING'
        
    Returns:
        List[str] 或 None: 解析后的状态列表，如果为空则返回None
        
    注意: 此函数仅处理内部解析，参数验证由依赖函数 validate_status_parameter 处理
    """
    if not status_param or not status_param.strip():
        return None
    
    # 分割逗号分隔的状态值，并去除空白
    statuses = [s.strip().upper() for s in status_param.split(',') if s.strip()]
    
    if not statuses:
        return None
    
    # 去重并返回
    return list(set(statuses))


@media_router.get("/files", response_model=MediaFilesResponse)
def get_media_files(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=500, description="返回的记录数限制（最大500）"), 
    status: Optional[str] = Depends(validate_status_parameter),
    search: Optional[str] = Query(None, description="按文件名模糊搜索"),
    sort: Optional[str] = Depends(validate_sort_parameter),
    db: Session = Depends(get_db)
):
    """
    查询媒体文件列表，支持分页、状态筛选、文件名搜索和排序。
    
    Args:
        skip: 跳过的记录数（用于分页）
        limit: 返回的记录数限制，默认20，最大500
        status: 可选的状态筛选条件，支持单个状态或逗号分隔的多个状态
        search: 可选的文件名或文件路径模糊搜索关键词
        sort: 排序方式，格式为 'field:direction'，如 'created_at:desc'
        db: 数据库会话依赖
        
    Returns:
        dict: 包含total、skip、limit和items的分页结果
    """
    # 构建基础查询
    statement = select(MediaFile)
    count_statement = select(func.count(MediaFile.id))
    
    # 如果提供了状态筛选，解析并验证状态值，添加过滤条件
    status_list = parse_status_parameter(status)
    if status_list is not None:
        if len(status_list) == 1:
            # 单个状态，使用等于条件
            statement = statement.where(MediaFile.status == status_list[0])
            count_statement = count_statement.where(MediaFile.status == status_list[0])
        else:
            # 多个状态，使用 IN 条件
            statement = statement.where(MediaFile.status.in_(status_list))
            count_statement = count_statement.where(MediaFile.status.in_(status_list))
    
    # 如果提供了搜索关键词，按空格分割成多个词，并对 original_filename 和 original_filepath 做 OR 模糊匹配
    # 示例: "foo bar" -> (original_filename ILIKE "%foo%" OR original_filepath ILIKE "%foo%") AND (original_filename ILIKE "%bar%" OR original_filepath ILIKE "%bar%")
    if search is not None and search.strip():
        # 拆分关键字并过滤空白项
        keywords = [kw for kw in search.strip().split() if kw]

        # 依次构造模糊匹配条件，全部关键字都需命中（AND），但每个关键字可以在文件名或路径中命中（OR）
        # 为防止SQL注入，使用参数化查询由 SQLModel 负责
        for kw in keywords:
            term = f"%{kw}%"
            condition = (MediaFile.original_filename.ilike(term) | MediaFile.original_filepath.ilike(term))
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
    
    # 获取总记录数
    total = db.exec(count_statement).one()
    
    # 解析并添加排序
    sort_column, is_descending = parse_sort_parameter(sort)
    if is_descending:
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())
    
    # 添加分页并执行查询
    statement = statement.offset(skip).limit(limit)
    media_files = db.exec(statement).all()
    
    # 计算分页边界字段
    has_next = skip + limit < total
    has_previous = skip > 0
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_next": has_next,
        "has_previous": has_previous,
        "items": media_files
    }


@media_router.get("/files/suggest", response_model=SuggestionResponse)
def suggest_filenames(
    keyword: str = Query(..., description="文件名前缀关键字"),
    limit: int = Query(20, ge=1, le=100, description="返回建议数量限制，默认20，最大100"),
    db: Session = Depends(get_db)
):
    """
    根据文件名前缀提供自动补全建议。
    
    Args:
        keyword: 文件名前缀关键字（必填）
        limit: 返回的建议数量限制，默认20，最大100
        db: 数据库会话依赖
        
    Returns:
        dict: 包含suggestions列表的响应
    """
    # 验证关键字不为空
    if not keyword or not keyword.strip():
        return {"suggestions": []}
    
    # 构建查询语句，使用 DISTINCT 去重，按文件名前缀匹配
    keyword_clean = keyword.strip()
    statement = (
        select(distinct(MediaFile.original_filename))
        .where(MediaFile.original_filename.ilike(f"{keyword_clean}%"))
        .limit(limit)
    )
    
    # 执行查询
    results = db.exec(statement).all()
    
    return {"suggestions": list(results)}


@media_router.get("/files/{file_id}", response_model=MediaFileDetail)
def get_media_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    根据文件ID获取单个媒体文件详情。
    
    Args:
        file_id: 媒体文件的ID
        db: 数据库会话依赖
        
    Returns:
        MediaFile: 媒体文件详情
        
    Raises:
        HTTPException: 当文件不存在时返回404错误
    """
    media_file = get_media_file_by_id(db, file_id)
    if not media_file:
        raise HTTPException(
            status_code=404,
            detail=f"媒体文件不存在: ID={file_id}"
        )
    
    return media_file


@media_router.get("/stats", response_model=Dict[str, int])
def get_media_stats(db: Session = Depends(get_db)):
    """
    获取按状态分组的媒体文件数量统计。
    
    Args:
        db: 数据库会话依赖
        
    Returns:
        dict: 按状态分组的文件数量统计，格式为 {status: count}
              如果数据库为空，返回空对象 {}
    """
    # 执行分组聚合查询
    statement = select(MediaFile.status, func.count(MediaFile.id)).group_by(MediaFile.status)
    results = db.exec(statement).all()
    
    # 如果查询结果为空，返回空对象
    if not results:
        return {}
    
    # 将结果转换为字典格式
    stats = {status: count for status, count in results}
    
    return stats


@media_router.post("/files/{file_id}/retry", response_model=RetryResponse)
async def retry_media_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    手动重试处理失败或无匹配的媒体文件。
    
    该接口仅将文件状态重置为 PENDING，由后台 Producer 统一重新入队。
    
    处理流程：
    1. API 验证文件存在性和状态合法性
    2. 将文件状态从失败状态（FAILED/NO_MATCH/CONFLICT）重置为 PENDING
    3. 后台 Producer 组件会定期轮询 PENDING 状态的文件
    4. Producer 将这些文件ID加入处理队列
    5. Worker 从队列获取文件ID并执行实际的媒体文件处理
    
    Args:
        file_id: 媒体文件的ID
        db: 数据库会话依赖
        
    Returns:
        dict: 包含以下字段的操作结果：
            - message: 操作结果描述
            - file_id: 文件ID
            - previous_status: 重置前的状态
            - current_status: 重置后的状态（始终为 PENDING）
        
    Raises:
        HTTPException: 
            - 404: 当文件不存在时
            - 400: 当文件状态不允许重试时（非 FAILED/NO_MATCH/CONFLICT）
            - 500: 当数据库操作失败时
    """
    # 从数据库获取媒体文件
    media_file = get_media_file_by_id(db, file_id)
    if not media_file:
        raise HTTPException(
            status_code=404,
            detail=f"媒体文件不存在: ID={file_id}"
        )
    
    # 检查文件状态是否允许重试
    if media_file.status not in RETRYABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"文件状态不允许重试: 当前状态={media_file.status}, 可重试状态: {', '.join(RETRYABLE_STATUSES)}"
        )
    
    try:
        # 保存原始状态
        previous_status = media_file.status
        
        # 更新状态为PENDING
        update_media_file_status(db, media_file, FileStatus.PENDING)
        
        logger.info(f"媒体文件 {file_id} 状态已重置为 PENDING，等待 Producer 重新排队")
        
        return {
            "message": "文件状态已成功重置，等待后台重新处理",
            "file_id": file_id,
            "previous_status": previous_status,
            "current_status": FileStatus.PENDING
        }
        
    except Exception as e:
        logger.error(f"重试媒体文件 {file_id} 时发生错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"重试操作失败: {str(e)}"
        )


# 批量操作请求模型
class BatchOperationRequest(BaseModel):
    file_ids: List[int]

# 批量操作响应模型
class BatchOperationResult(BaseModel):
    file_id: int
    success: bool
    error: Optional[str] = None

class BatchOperationResponse(BaseModel):
    message: str
    results: List[BatchOperationResult]


@media_router.post("/files/batch-retry", response_model=BatchOperationResponse)
async def batch_retry_media_files(
    request: BatchOperationRequest,
    db: Session = Depends(get_db)
):
    """
    批量重试处理失败或无匹配的媒体文件。
    
    该接口仅将文件状态重置为 PENDING，由后台 Producer 统一重新入队。
    
    Args:
        request: 包含文件ID列表的请求体
        db: 数据库会话依赖
        
    Returns:
        dict: 包含批量操作结果的响应
        
    Raises:
        HTTPException: 当请求无效时
    """
    if not request.file_ids:
        raise HTTPException(
            status_code=400,
            detail="文件ID列表不能为空"
        )
    
    if len(request.file_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="批量操作文件数量不能超过100个"
        )
    
    results = []
    success_count = 0
    
    for file_id in request.file_ids:
        try:
            # 从数据库获取媒体文件
            media_file = get_media_file_by_id(db, file_id)
            if not media_file:
                results.append(BatchOperationResult(
                    file_id=file_id,
                    success=False,
                    error=f"文件不存在: ID={file_id}"
                ))
                continue
            
            # 检查文件状态是否允许重试
            if media_file.status not in RETRYABLE_STATUSES:
                results.append(BatchOperationResult(
                    file_id=file_id,
                    success=False,
                    error=f"文件状态不允许重试: 当前状态={media_file.status}"
                ))
                continue
            
            # 更新状态为PENDING
            update_media_file_status(db, media_file, FileStatus.PENDING)
            
            results.append(BatchOperationResult(
                file_id=file_id,
                success=True
            ))
            success_count += 1
            
            logger.info(f"媒体文件 {file_id} 状态已重置为 PENDING，等待 Producer 重新排队")
            
        except Exception as e:
            logger.error(f"重试媒体文件 {file_id} 时发生错误: {e}")
            results.append(BatchOperationResult(
                file_id=file_id,
                success=False,
                error=f"重试操作失败: {str(e)}"
            ))
    
    total_count = len(request.file_ids)
    failure_count = total_count - success_count
    
    return {
        "message": f"批量重试完成：成功 {success_count} 个，失败 {failure_count} 个",
        "results": results
    }


@media_router.post("/files/batch-delete", response_model=BatchOperationResponse)
async def batch_delete_media_files(
    request: BatchOperationRequest,
    db: Session = Depends(get_db)
):
    """
    批量删除媒体文件记录（可选功能）。
    
    注意：此操作仅删除数据库记录，不删除实际文件。
    
    Args:
        request: 包含文件ID列表的请求体
        db: 数据库会话依赖
        
    Returns:
        dict: 包含批量操作结果的响应
        
    Raises:
        HTTPException: 当请求无效时
    """
    if not request.file_ids:
        raise HTTPException(
            status_code=400,
            detail="文件ID列表不能为空"
        )
    
    if len(request.file_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="批量操作文件数量不能超过100个"
        )
    
    results = []
    success_count = 0
    
    for file_id in request.file_ids:
        try:
            # 从数据库获取媒体文件
            media_file = get_media_file_by_id(db, file_id)
            if not media_file:
                results.append(BatchOperationResult(
                    file_id=file_id,
                    success=False,
                    error=f"文件不存在: ID={file_id}"
                ))
                continue
            
            # 删除记录
            db.delete(media_file)
            db.commit()
            
            results.append(BatchOperationResult(
                file_id=file_id,
                success=True
            ))
            success_count += 1
            
            logger.info(f"媒体文件记录 {file_id} 已删除")
            
        except Exception as e:
            logger.error(f"删除媒体文件 {file_id} 时发生错误: {e}")
            db.rollback()
            results.append(BatchOperationResult(
                file_id=file_id,
                success=False,
                error=f"删除操作失败: {str(e)}"
            ))
    
    total_count = len(request.file_ids)
    failure_count = total_count - success_count
    
    return {
        "message": f"批量删除完成：成功 {success_count} 个，失败 {failure_count} 个",
        "results": results
    } 