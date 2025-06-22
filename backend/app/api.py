"""
API路由模块

提供ClearMedia的REST API端点，包括媒体文件查询、统计等功能。
"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select, func, or_, distinct
from loguru import logger

from .db import get_db
from .core.models import MediaFile, FileStatus
from .crud import get_media_file_by_id, update_media_file_status


router = APIRouter(prefix="/api", tags=["media"])


@router.get("/files")
def get_media_files(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=500, description="返回的记录数限制（最大500）"), 
    status: Optional[str] = Query(None, description=f"按状态筛选: {FileStatus.PENDING}, {FileStatus.PROCESSING}, {FileStatus.COMPLETED}, {FileStatus.FAILED}, {FileStatus.CONFLICT}, {FileStatus.NO_MATCH}"),
    search: Optional[str] = Query(None, description="按文件名模糊搜索"),
    sort: Optional[Literal["created_at:asc", "created_at:desc"]] = Query("created_at:desc", description="排序方式: created_at:asc 或 created_at:desc"),
    db: Session = Depends(get_db)
):
    """
    查询媒体文件列表，支持分页、状态筛选、文件名搜索和排序。
    
    Args:
        skip: 跳过的记录数（用于分页）
        limit: 返回的记录数限制，默认20，最大500
        status: 可选的状态筛选条件
        search: 可选的文件名模糊搜索关键词
        sort: 排序方式，默认按创建时间降序
        db: 数据库会话依赖
        
    Returns:
        dict: 包含total、skip、limit和items的分页结果
    """
    # 构建基础查询
    statement = select(MediaFile)
    count_statement = select(func.count(MediaFile.id))
    
    # 如果提供了状态筛选，验证状态值并添加过滤条件
    if status is not None:
        # 验证状态值是否有效
        valid_statuses = [
            FileStatus.PENDING, FileStatus.PROCESSING, FileStatus.COMPLETED,
            FileStatus.FAILED, FileStatus.CONFLICT, FileStatus.NO_MATCH
        ]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=422,
                detail=f"无效的状态值: {status}. 有效值: {', '.join(valid_statuses)}"
            )
        
        statement = statement.where(MediaFile.status == status)
        count_statement = count_statement.where(MediaFile.status == status)
    
    # 如果提供了搜索关键词，添加文件名模糊搜索条件
    if search is not None and search.strip():
        search_term = f"%{search.strip()}%"
        search_condition = or_(
            MediaFile.original_filename.ilike(search_term),
            MediaFile.original_filepath.ilike(search_term)
        )
        statement = statement.where(search_condition)
        count_statement = count_statement.where(search_condition)
    
    # 获取总记录数
    total = db.exec(count_statement).one()
    
    # 添加排序
    if sort == "created_at:asc":
        statement = statement.order_by(MediaFile.created_at.asc())
    else:  # 默认为 "created_at:desc"
        statement = statement.order_by(MediaFile.created_at.desc())
    
    # 添加分页并执行查询
    statement = statement.offset(skip).limit(limit)
    media_files = db.exec(statement).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": media_files
    }


@router.get("/files/suggest")
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


@router.get("/files/{file_id}")
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


@router.get("/stats")
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


@router.post("/files/{file_id}/retry")
async def retry_media_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    手动重试处理失败或无匹配的媒体文件。
    
    Args:
        file_id: 媒体文件的ID
        request: FastAPI请求对象，用于访问app.state
        db: 数据库会话依赖
        
    Returns:
        dict: 操作结果信息
        
    Raises:
        HTTPException: 当文件不存在或状态不允许重试时抛出
    """
    # 从数据库获取媒体文件
    media_file = get_media_file_by_id(db, file_id)
    if not media_file:
        raise HTTPException(
            status_code=404,
            detail=f"媒体文件不存在: ID={file_id}"
        )
    
    # 检查文件状态是否允许重试
    retryable_statuses = [FileStatus.FAILED, FileStatus.NO_MATCH, FileStatus.CONFLICT]
    if media_file.status not in retryable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"文件状态不允许重试: 当前状态={media_file.status}, 可重试状态: {', '.join(retryable_statuses)}"
        )
    
    # 获取队列实例
    media_queue = request.app.state.media_queue
    
    try:
        # 保存原始状态
        previous_status = media_file.status
        
        # 更新状态为PENDING
        update_media_file_status(db, media_file, FileStatus.PENDING)
        
        # 将文件ID放入处理队列
        await media_queue.put(file_id)
        
        logger.info(f"媒体文件 {file_id} 已重新排队处理")
        
        return {
            "message": "文件已成功排队重新处理",
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