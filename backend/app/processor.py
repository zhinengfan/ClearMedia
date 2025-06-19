"""媒体文件处理器模块

负责在文件扫描入库后，执行一个健壮的、带重试的、可配置的处理流水线。
处理流程：LLM分析 -> TMDB匹配 -> 文件链接 -> 状态更新
"""

from __future__ import annotations

from typing import NamedTuple, Callable
from pathlib import Path
from sqlmodel import Session
from loguru import logger

from .config import Settings
from .core.models import MediaFile, FileStatus
from .core.linker import create_hardlink, LinkResult


class ProcessResult(NamedTuple):
    """处理结果"""
    success: bool
    message: str
    media_file_id: int


def generate_new_path(
    media_info: dict, 
    llm_guess: dict | None,
    original_filepath: str, 
    target_dir: Path
) -> Path:
    """根据媒体信息生成标准的目标路径
    
    Args:
        media_info: TMDB返回的媒体信息
        llm_guess: LLM分析结果，用于获取季/集信息
        original_filepath: 原始文件路径
        target_dir: 目标目录
        
    Returns:
        Path: 生成的新文件路径
    """
    # 获取原始文件的扩展名
    original_path = Path(original_filepath)
    file_extension = original_path.suffix
    
    # 根据媒体类型生成路径
    if "name" in media_info:  # 电视剧
        title = media_info["name"]
        year = ""
        if "first_air_date" in media_info and media_info["first_air_date"]:
            year = media_info["first_air_date"][:4]  # 提取年份
        
        # 清理标题中的特殊字符
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        if year:
            folder_name = f"{clean_title} ({year})"
        else:
            folder_name = clean_title
            
        # 从 LLM 结果中获取季和集信息
        season = 1  # 默认第一季
        episode = None
        if llm_guess:
            season = llm_guess.get("season", 1)
            episode = llm_guess.get("episode")
        
        if episode is not None:
            filename = f"{clean_title} S{season:02d}E{episode:02d}{file_extension}"
        else:
            # 如果没有剧集信息，则使用原始文件名，防止覆盖
            filename = f"{folder_name}{file_extension}"

        return target_dir / "TV Shows" / folder_name / filename
        
    else:  # 电影
        title = media_info.get("title", "Unknown")
        year = ""
        if "release_date" in media_info and media_info["release_date"]:
            year = media_info["release_date"][:4]  # 提取年份
        
        # 清理标题中的特殊字符
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        if year:
            filename = f"{clean_title} ({year}){file_extension}"
        else:
            filename = f"{clean_title}{file_extension}"
            
        return target_dir / "Movies" / filename


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
    
    # 成功标志和状态控制
    is_successful = False
    error_msg = ""
    final_status = None  # 如果设置了特定状态，则不在finally中覆盖
    
    # 初始状态更新：将状态设为 PROCESSING
    try:
        with db_session_factory() as db:
            media_file = db.get(MediaFile, media_file_id)
            if not media_file:
                return ProcessResult(
                    success=False,
                    message=f"未找到ID为 {media_file_id} 的媒体文件",
                    media_file_id=media_file_id
                )
            
            media_file.status = FileStatus.PROCESSING
            db.add(media_file)
            db.commit()
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
        # 获取当前媒体文件信息用于处理
        with db_session_factory() as db:
            media_file = db.get(MediaFile, media_file_id)
            if not media_file:
                raise ValueError(f"未找到媒体文件 {media_file_id}")
            original_filename = media_file.original_filename
            original_filepath = media_file.original_filepath
        
        ctx_logger.info(f"开始处理文件: {original_filename}")
        
        # 第一步：LLM 分析文件名（如果启用）
        llm_result = None
        if settings.ENABLE_LLM:
            ctx_logger.info("开始 LLM 分析文件名")
            from .core.llm import analyze_filename
            llm_result = await analyze_filename(original_filename)
            ctx_logger.info(f"LLM 分析完成: {llm_result}")
        else:
            ctx_logger.info("LLM 功能已禁用，跳过文件名分析")
        
        # 第二步：TMDB 搜索媒体信息（如果启用且有 LLM 结果）
        tmdb_result = None
        if settings.ENABLE_TMDB and llm_result:
            ctx_logger.info("开始 TMDB 搜索媒体信息")
            from .core.tmdb import search_media
            tmdb_result = await search_media(llm_result)
            if tmdb_result:
                ctx_logger.info(f"TMDB 搜索成功: ID={tmdb_result['tmdb_id']}, 类型={tmdb_result['media_type']}")
            else:
                ctx_logger.warning("TMDB 搜索未找到匹配结果")
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
                with db_session_factory() as db:
                    media_file = db.get(MediaFile, media_file_id)
                    if media_file:
                        if llm_result:
                            media_file.llm_guess = llm_result
                        if tmdb_result:
                            media_file.tmdb_id = tmdb_result["tmdb_id"]
                            media_file.media_type = tmdb_result["media_type"]
                            media_file.processed_data = tmdb_result["processed_data"]
                        media_file.status = FileStatus.CONFLICT
                        media_file.error_message = f"目标路径已存在: {target_path}"
                        db.add(media_file)
                        db.commit()
                
                # 设置最终状态为CONFLICT，防止finally块覆盖
                final_status = FileStatus.CONFLICT
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
        
        # 第四步：原子性更新所有字段
        with db_session_factory() as db:
            media_file = db.get(MediaFile, media_file_id)
            if not media_file:
                raise ValueError(f"最终更新时未找到媒体文件 {media_file_id}")
            
            # 批量更新所有处理结果字段
            if llm_result:
                media_file.llm_guess = llm_result
            
            if tmdb_result:
                media_file.tmdb_id = tmdb_result["tmdb_id"]
                media_file.media_type = tmdb_result["media_type"]
                media_file.processed_data = tmdb_result["processed_data"]
            
            # 更新新文件路径
            if new_filepath:
                media_file.new_filepath = new_filepath
            
            # 一次性提交所有更改
            db.add(media_file)
            db.commit()
            db.refresh(media_file)
            
            ctx_logger.info("所有处理结果已批量更新到数据库")
        
        # 标记处理成功
        is_successful = True
        ctx_logger.info("媒体文件处理成功完成")
        
    except Exception as e:
        ctx_logger.error(f"处理过程中发生错误: {e}")
        error_msg = str(e)
        is_successful = False
        
        # 即使失败，也保存已经获取的数据
        try:
            with db_session_factory() as db:
                media_file = db.get(MediaFile, media_file_id)
                if media_file:
                    # 保存LLM结果
                    if 'llm_result' in locals() and llm_result:
                        media_file.llm_guess = llm_result
                    
                    # 保存TMDB结果
                    if 'tmdb_result' in locals() and tmdb_result:
                        media_file.tmdb_id = tmdb_result["tmdb_id"]
                        media_file.media_type = tmdb_result["media_type"]
                        media_file.processed_data = tmdb_result["processed_data"]
                    
                    db.add(media_file)
                    db.commit()
                    ctx_logger.info("失败时已保存获取到的数据")
        except Exception as save_e:
            ctx_logger.error(f"保存失败数据时发生错误: {save_e}")
    
    finally:
        # 最终状态更新：使用新会话
        # 只有在没有设置特定状态时才更新状态
        if final_status is None:
            try:
                with db_session_factory() as db:
                    media_file = db.get(MediaFile, media_file_id)
                    if media_file:
                        if is_successful:
                            media_file.status = FileStatus.COMPLETED
                            media_file.error_message = None
                            ctx_logger.info("最终状态已更新为 COMPLETED")
                        else:
                            media_file.status = FileStatus.FAILED
                            media_file.error_message = error_msg
                            ctx_logger.warning("最终状态已更新为 FAILED")
                        
                        db.add(media_file)
                        db.commit()
                    else:
                        ctx_logger.error(f"最终状态更新时未找到媒体文件 {media_file_id}")
                        
            except Exception as e:
                ctx_logger.error(f"最终状态更新失败: {e}")
        else:
            ctx_logger.info(f"跳过最终状态更新，已设置为: {final_status}")
    
    return ProcessResult(
        success=is_successful,
        message="处理成功" if is_successful else f"处理失败: {error_msg}",
        media_file_id=media_file_id
    ) 