"""媒体文件处理器模块

负责在文件扫描入库后，执行一个健壮的、带重试的、可配置的处理流水线。
处理流程：LLM分析 -> TMDB匹配 -> 文件链接 -> 状态更新
"""

from __future__ import annotations

from typing import Callable
from pathlib import Path
from sqlmodel import Session
from loguru import logger

from ...config import Settings
from ...core.models import MediaFile
from ...core.linker import create_hardlink, LinkResult
from .types import ProcessResult
from .path_generator import generate_new_path
from . import status_manager


async def process_media_file(
    media_file_id: int,
    db_session_factory: Callable[[], Session], 
    settings: Settings
) -> ProcessResult:
    """处理媒体文件的核心函数
    
    Args:
        media_file_id: 待处理的媒体文件ID
        db_session_factory: 数据库会话工厂函数
        settings: 应用配置
        
    Returns:
        ProcessResult: 处理结果，包含成功状态、消息和文件ID
        
    处理流程：
    1. 更新状态为PROCESSING
    2. LLM分析文件名（如果启用）
    3. TMDB匹配信息（如果启用且LLM分析成功）
    4. 创建硬链接并更新路径
    5. 更新最终状态为COMPLETED或FAILED
    """
    # 创建上下文日志
    ctx_logger = logger.bind(media_file_id=media_file_id)
    ctx_logger.info("开始处理媒体文件")
    
    # 初始状态检查和更新
    try:
        with db_session_factory() as db:
            media_file = db.get(MediaFile, media_file_id)
            if not media_file:
                return ProcessResult(
                    success=False,
                    message=f"未找到ID为 {media_file_id} 的媒体文件",
                    media_file_id=media_file_id
                )
            original_filename = media_file.original_filename
            original_filepath = media_file.original_filepath
        
        # 设置为处理中状态
        status_manager.set_processing(db_session_factory, media_file_id)
        ctx_logger.info("已将文件状态更新为 PROCESSING")
        
    except Exception as e:
        ctx_logger.error(f"初始状态更新失败: {e}")
        return ProcessResult(
            success=False,
            message=f"初始状态更新失败: {e}",
            media_file_id=media_file_id
        )
    
    # 核心处理逻辑
    try:
        ctx_logger.info(f"开始处理文件: {original_filename}")
        
        # 第一步：LLM 分析文件名（如果启用）
        llm_result = None
        if settings.ENABLE_LLM:
            ctx_logger.info("开始 LLM 分析文件名")
            from ...core.llm import analyze_filename
            llm_result = await analyze_filename(original_filename)
            ctx_logger.info(f"LLM 分析完成: {llm_result}")
        else:
            ctx_logger.info("LLM 功能已禁用，跳过文件名分析")
        
        # 第二步：TMDB 搜索媒体信息（如果启用且有 LLM 结果）
        tmdb_result = None
        if settings.ENABLE_TMDB and llm_result:
            ctx_logger.info("开始 TMDB 搜索媒体信息")
            from ...core.tmdb import search_media
            tmdb_result = await search_media(llm_result)
            if tmdb_result:
                ctx_logger.info(f"TMDB 搜索成功: ID={tmdb_result['tmdb_id']}, 类型={tmdb_result['media_type']}")
            else:
                ctx_logger.warning("TMDB 搜索未找到匹配结果")
                # 当TMDB启用但未找到匹配时，设置为NO_MATCH状态
                status_manager.set_no_match(
                    db_session_factory,
                    media_file_id,
                    llm_guess=llm_result
                )
                return ProcessResult(
                    success=False,
                    message="No TMDB match found",
                    media_file_id=media_file_id
                )
        else:
            if not settings.ENABLE_TMDB:
                ctx_logger.info("TMDB 功能已禁用，跳过媒体搜索")
            elif not llm_result:
                ctx_logger.info("无 LLM 分析结果，跳过 TMDB 搜索")
        
        # 第三步：文件链接操作（如果有 TMDB 结果）
        new_filepath = None
        if tmdb_result and tmdb_result.get("processed_data"):
            ctx_logger.info("开始创建文件硬链接")
            processed_data = tmdb_result["processed_data"]
            
            # 生成目标路径
            target_path = generate_new_path(
                processed_data, llm_result, original_filepath, settings.TARGET_DIR
            )
            ctx_logger.info(f"生成目标路径: {target_path}")
            
            # 创建硬链接
            link_result = create_hardlink(Path(original_filepath), target_path)
            
            if link_result == LinkResult.LINK_SUCCESS:
                new_filepath = str(target_path)
                ctx_logger.info(f"硬链接创建成功: {target_path}")
            elif link_result == LinkResult.LINK_FAILED_CONFLICT:
                ctx_logger.warning(f"目标路径已存在，设置状态为 CONFLICT: {target_path}")
                # 对于冲突情况，设置为 CONFLICT 状态并返回
                status_manager.set_conflict(
                    db_session_factory,
                    media_file_id,
                    str(target_path),
                    llm_guess=llm_result,
                    tmdb_id=tmdb_result["tmdb_id"] if tmdb_result else None,
                    media_type=tmdb_result["media_type"] if tmdb_result else None,
                    processed_data=tmdb_result["processed_data"] if tmdb_result else None
                )
                return ProcessResult(
                    success=False,
                    message="文件处理冲突: 目标路径已存在",
                    media_file_id=media_file_id
                )
            else:
                # 其他链接失败情况
                error_msg = f"硬链接创建失败: {link_result}"
                ctx_logger.error(error_msg)
                raise ValueError(error_msg)
        else:
            ctx_logger.info("无 TMDB 结果，跳过文件链接")
        
        # 第四步：设置为完成状态
        status_manager.set_completed(
            db_session_factory,
            media_file_id,
            new_filepath=new_filepath,
            llm_guess=llm_result,
            tmdb_id=tmdb_result["tmdb_id"] if tmdb_result else None,
            media_type=tmdb_result["media_type"] if tmdb_result else None,
            processed_data=tmdb_result["processed_data"] if tmdb_result else None
        )
        
        ctx_logger.info("媒体文件处理成功完成")
        return ProcessResult(
            success=True,
            message="处理成功",
            media_file_id=media_file_id
        )
        
    except Exception as e:
        ctx_logger.error(f"处理过程中发生错误: {e}")
        error_msg = str(e)
        
        # 即使失败，也保存已经获取的数据
        status_manager.set_failed(
            db_session_factory,
            media_file_id,
            error_msg,
            llm_guess=llm_result if 'llm_result' in locals() else None,
            tmdb_id=tmdb_result["tmdb_id"] if 'tmdb_result' in locals() and tmdb_result else None,
            media_type=tmdb_result["media_type"] if 'tmdb_result' in locals() and tmdb_result else None,
            processed_data=tmdb_result["processed_data"] if 'tmdb_result' in locals() and tmdb_result else None
        )
        
        return ProcessResult(
            success=False,
            message=f"处理失败: {error_msg}",
            media_file_id=media_file_id
        ) 