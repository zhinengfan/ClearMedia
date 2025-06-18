"""
扫描器模块

提供目录扫描功能，用于发现新的媒体文件并添加到数据库中。
包含同步扫描函数和异步后台任务循环，支持优雅关闭。
"""

import asyncio
from pathlib import Path
from typing import Set, Callable

from loguru import logger
from sqlmodel import Session

from . import crud
from .config import Settings

# 常量定义
SCANNER_LOG_PREFIX = "[Scanner]"


def scan_directory_once(
    db_session: Session, 
    source_dir: Path, 
    allowed_extensions: Set[str]
) -> int:
    """
    扫描指定目录一次，发现新的媒体文件并添加到数据库。
    
    Args:
        db_session: 数据库会话
        source_dir: 要扫描的源目录路径
        allowed_extensions: 允许的文件扩展名集合（如 {'.mp4', '.mkv'}）
        
    Returns:
        int: 新添加到数据库的文件数量
    """
    logger.debug(f"{SCANNER_LOG_PREFIX} 开始扫描目录: {source_dir}")
    new_files_count = 0
    
    # 确保源目录存在
    if not source_dir.exists() or not source_dir.is_dir():
        logger.warning(f"{SCANNER_LOG_PREFIX} 目录不存在或不是有效目录: {source_dir}")
        return new_files_count
    
    try:
        # 遍历目录中的所有文件
        files_found = 0
        for file_path in source_dir.iterdir():
            # 跳过非文件项（如子目录）
            if not file_path.is_file():
                continue
                
            files_found += 1
            
            # 检查文件扩展名是否在允许列表中
            if file_path.suffix.lower() not in allowed_extensions:
                logger.trace(f"{SCANNER_LOG_PREFIX} 跳过非媒体文件: {file_path.name}")
                continue
                
            # 获取文件的统计信息用于数据库查询
            try:
                stat_info = file_path.stat()
                inode = stat_info.st_ino
                device_id = stat_info.st_dev
            except OSError as e:
                logger.error(f"{SCANNER_LOG_PREFIX} 无法获取文件信息 {file_path}: {e}")
                continue
                
            # 检查文件是否已存在于数据库中
            try:
                existing_media_file = crud.get_media_file_by_inode_device(
                    db_session, inode, device_id
                )
            except Exception as e:
                logger.error(f"{SCANNER_LOG_PREFIX} 数据库查询失败 {file_path}: {e}")
                continue
            
            # 如果文件不存在于数据库中，创建新记录
            if existing_media_file is None:
                try:
                    crud.create_media_file(db_session, file_path)
                    new_files_count += 1
                    logger.info(f"{SCANNER_LOG_PREFIX} 新增媒体文件: {file_path.name}")
                except Exception as e:
                    logger.error(f"{SCANNER_LOG_PREFIX} 创建媒体文件记录失败 {file_path}: {e}")
                    continue
            else:
                logger.trace(f"{SCANNER_LOG_PREFIX} 文件已存在于数据库: {file_path.name}")
        
        logger.debug(
            f"{SCANNER_LOG_PREFIX} 扫描完成 - 总文件: {files_found}, "
            f"新增媒体文件: {new_files_count}"
        )
        
    except Exception as e:
        logger.error(f"{SCANNER_LOG_PREFIX} 扫描目录时发生异常 {source_dir}: {e}")
    
    return new_files_count


async def background_scanner_task(
    db_session_factory: Callable[[], Session],
    settings: Settings,
    stop_event: asyncio.Event = None
) -> None:
    """
    后台扫描任务，定期扫描源目录并处理新文件。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        settings: 应用配置对象
        stop_event: 可选的停止事件，用于优雅关闭
    """
    if stop_event is None:
        stop_event = asyncio.Event()
    
    logger.info(
        f"{SCANNER_LOG_PREFIX} 后台扫描任务启动 - "
        f"源目录: {settings.SOURCE_DIR}, "
        f"扫描间隔: {settings.SCAN_INTERVAL_SECONDS}秒"
    )
    
    # 使用配置中的视频文件扩展名
    allowed_extensions = set(ext.strip() for ext in settings.VIDEO_EXTENSIONS.split(',') if ext.strip())
    scan_count = 0
    
    try:
        while not stop_event.is_set():
            scan_count += 1
            logger.debug(f"{SCANNER_LOG_PREFIX} 开始第 {scan_count} 次扫描")
            
            try:
                # 在异步环境中运行同步的数据库操作
                def _sync_scan():
                    with db_session_factory() as db_session:
                        return scan_directory_once(
                            db_session, 
                            settings.SOURCE_DIR, 
                            allowed_extensions
                        )
                
                # 使用 asyncio.to_thread 在线程池中执行同步操作
                new_files_count = await asyncio.to_thread(_sync_scan)
                
                if new_files_count > 0:
                    logger.info(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描发现 {new_files_count} 个新文件")
                else:
                    logger.debug(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描未发现新文件")
                    
            except Exception as e:
                logger.error(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描失败: {e}")
            
            # 等待指定间隔或停止事件
            try:
                await asyncio.wait_for(
                    stop_event.wait(), 
                    timeout=settings.SCAN_INTERVAL_SECONDS
                )
                # 如果 stop_event 被设置，退出循环
                break
            except asyncio.TimeoutError:
                # 超时是正常的，继续下一次扫描
                continue
                
    except asyncio.CancelledError:
        logger.info(f"{SCANNER_LOG_PREFIX} 后台扫描任务被取消")
        raise
    except Exception as e:
        logger.error(f"{SCANNER_LOG_PREFIX} 后台扫描任务异常退出: {e}")
        raise
    finally:
        logger.info(
            f"{SCANNER_LOG_PREFIX} 后台扫描任务结束 - "
            f"总共执行了 {scan_count} 次扫描"
        ) 