"""媒体文件状态管理模块

负责原子性地更新媒体文件的状态和相关字段
"""

from typing import Callable
from sqlmodel import Session
from loguru import logger

from ...core.models import MediaFile, FileStatus


def update_status(
    db_session_factory: Callable[[], Session],
    media_file_id: int,
    *,
    status: FileStatus,
    error_message: str | None = None,
    extra_fields: dict | None = None,
) -> None:
    """统一的状态更新入口（原子提交）
    
    Args:
        db_session_factory: 数据库会话工厂函数
        media_file_id: 媒体文件ID
        status: 要设置的状态
        error_message: 错误消息（可选）
        extra_fields: 额外要更新的字段（可选）
    """
    try:
        with db_session_factory() as db:
            media_file = db.get(MediaFile, media_file_id)
            if not media_file:
                logger.error(f"Media file {media_file_id} not found")
                return
            
            # 更新额外字段
            if extra_fields:
                for k, v in extra_fields.items():
                    setattr(media_file, k, v)
            
            # 更新状态和错误消息
            media_file.status = status
            media_file.error_message = error_message
            
            db.add(media_file)
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed to update status for media file {media_file_id}: {e}")


def set_processing(
    db_session_factory: Callable[[], Session],
    media_file_id: int
) -> None:
    """设置为处理中状态"""
    update_status(
        db_session_factory,
        media_file_id,
        status=FileStatus.PROCESSING,
        error_message=None
    )


def set_completed(
    db_session_factory: Callable[[], Session],
    media_file_id: int,
    *,
    new_filepath: str | None = None,
    llm_guess: dict | None = None,
    tmdb_id: int | None = None,
    media_type: str | None = None,
    processed_data: dict | None = None
) -> None:
    """设置为完成状态"""
    extra_fields = {}
    
    if new_filepath is not None:
        extra_fields["new_filepath"] = new_filepath
    if llm_guess is not None:
        extra_fields["llm_guess"] = llm_guess
    if tmdb_id is not None:
        extra_fields["tmdb_id"] = tmdb_id
    if media_type is not None:
        extra_fields["media_type"] = media_type
    if processed_data is not None:
        extra_fields["processed_data"] = processed_data
    
    update_status(
        db_session_factory,
        media_file_id,
        status=FileStatus.COMPLETED,
        error_message=None,
        extra_fields=extra_fields
    )


def set_failed(
    db_session_factory: Callable[[], Session],
    media_file_id: int,
    error_message: str,
    *,
    llm_guess: dict | None = None,
    tmdb_id: int | None = None,
    media_type: str | None = None,
    processed_data: dict | None = None
) -> None:
    """设置为失败状态"""
    extra_fields = {}
    
    if llm_guess is not None:
        extra_fields["llm_guess"] = llm_guess
    if tmdb_id is not None:
        extra_fields["tmdb_id"] = tmdb_id
    if media_type is not None:
        extra_fields["media_type"] = media_type
    if processed_data is not None:
        extra_fields["processed_data"] = processed_data
    
    update_status(
        db_session_factory,
        media_file_id,
        status=FileStatus.FAILED,
        error_message=error_message,
        extra_fields=extra_fields
    )


def set_no_match(
    db_session_factory: Callable[[], Session],
    media_file_id: int,
    *,
    llm_guess: dict | None = None
) -> None:
    """设置为无匹配状态"""
    extra_fields = {}
    
    if llm_guess is not None:
        extra_fields["llm_guess"] = llm_guess
    
    update_status(
        db_session_factory,
        media_file_id,
        status=FileStatus.NO_MATCH,
        error_message="No TMDB match found",
        extra_fields=extra_fields
    )


def set_conflict(
    db_session_factory: Callable[[], Session],
    media_file_id: int,
    conflict_path: str,
    *,
    llm_guess: dict | None = None,
    tmdb_id: int | None = None,
    media_type: str | None = None,
    processed_data: dict | None = None
) -> None:
    """设置为冲突状态"""
    extra_fields = {}
    
    if llm_guess is not None:
        extra_fields["llm_guess"] = llm_guess
    if tmdb_id is not None:
        extra_fields["tmdb_id"] = tmdb_id
    if media_type is not None:
        extra_fields["media_type"] = media_type
    if processed_data is not None:
        extra_fields["processed_data"] = processed_data
    
    update_status(
        db_session_factory,
        media_file_id,
        status=FileStatus.CONFLICT,
        error_message=f"目标路径已存在: {conflict_path}",
        extra_fields=extra_fields
    ) 