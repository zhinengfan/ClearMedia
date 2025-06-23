"""
扫描器模块

提供目录扫描功能，用于发现新的媒体文件并添加到数据库中。
包含同步扫描函数和异步后台任务循环，支持优雅关闭。
作为生产者，将发现的媒体文件ID放入队列供处理器消费。
"""

import asyncio
import os
from pathlib import Path
from typing import Set, Callable, List

from loguru import logger
from sqlmodel import Session

from ... import crud
from ...config import Settings

# 常量定义
SCANNER_LOG_PREFIX = "[Scanner]"


def _log_scan_error(e: OSError):
    """os.walk的错误回调函数，仅记录错误并继续"""
    logger.warning(f"{SCANNER_LOG_PREFIX} 扫描时访问路径失败，已跳过: {e}")


def scan_directory_once(
    db_session: Session, 
    settings: Settings, 
    allowed_extensions: Set[str]
) -> List[int]:
    """
    扫描指定目录一次，发现新的媒体文件并添加到数据库。
    
    Args:
        db_session: 数据库会话
        settings: 应用配置
        allowed_extensions: 允许的文件扩展名集合（如 {'.mp4', '.mkv'}）
        
    Returns:
        List[int]: 新添加到数据库的媒体文件ID列表
    """
    source_dir = settings.SOURCE_DIR
    target_dir_abs = str(settings.TARGET_DIR.resolve())
    min_file_size_bytes = settings.MIN_FILE_SIZE_MB * 1024 * 1024

    logger.debug(f"{SCANNER_LOG_PREFIX} 开始扫描目录: {source_dir}")
    new_file_ids = []
    
    # 确保源目录存在
    if not source_dir.exists() or not source_dir.is_dir():
        logger.warning(f"{SCANNER_LOG_PREFIX} 目录不存在或不是有效目录: {source_dir}")
        return new_file_ids
    
    try:
        files_found = 0
        walk_iterator = os.walk(
            source_dir, 
            onerror=_log_scan_error, 
            followlinks=settings.SCAN_FOLLOW_SYMLINKS
        )

        for dirpath, dirnames, filenames in walk_iterator:
            # 建议2: 跳过目标目录以提高效率
            # 使用resolve()确保路径是绝对的，然后用字符串比较
            if settings.SCAN_EXCLUDE_TARGET_DIR and str(Path(dirpath).resolve()).startswith(target_dir_abs):
                logger.trace(f"{SCANNER_LOG_PREFIX} 跳过目标目录及其子目录: {dirpath}")
                # 清空dirnames, 告诉os.walk不要再进入这个目录的子目录
                dirnames[:] = []
                continue

            for filename in filenames:
                files_found += 1
                file_path = Path(dirpath) / filename
            
                # 检查文件扩展名是否在允许列表中
                if file_path.suffix.lower() not in allowed_extensions:
                    logger.trace(f"{SCANNER_LOG_PREFIX} 跳过非媒体文件: {file_path.name}")
                    continue
                
                # 获取文件的统计信息用于后续检查
                try:
                    stat_info = file_path.stat()
                except OSError as e:
                    logger.error(f"{SCANNER_LOG_PREFIX} 无法获取文件信息 {file_path}: {e}")
                    continue

                # 建议5: 检查文件大小
                if settings.MIN_FILE_SIZE_MB > 0 and stat_info.st_size < min_file_size_bytes:
                    logger.trace(f"{SCANNER_LOG_PREFIX} 跳过小文件 (<{settings.MIN_FILE_SIZE_MB}MB): {file_path.name}")
                    continue
                    
                inode = stat_info.st_ino
                device_id = stat_info.st_dev
                
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
                        new_media_file = crud.create_media_file(db_session, file_path)
                        new_file_ids.append(new_media_file.id)
                        logger.info(f"{SCANNER_LOG_PREFIX} 新增媒体文件: {file_path.name} (ID: {new_media_file.id})")
                    except Exception as e:
                        logger.error(f"{SCANNER_LOG_PREFIX} 创建媒体文件记录失败 {file_path}: {e}")
                        continue
                else:
                    logger.trace(f"{SCANNER_LOG_PREFIX} 文件已存在于数据库: {file_path.name}")
        
        logger.debug(
            f"{SCANNER_LOG_PREFIX} 扫描完成 - 总文件: {files_found}, "
            f"新增媒体文件: {len(new_file_ids)}"
        )
        
    except Exception as e:
        logger.error(f"{SCANNER_LOG_PREFIX} 扫描目录时发生异常 {source_dir}: {e}")
    
    return new_file_ids


async def background_scanner_task(
    db_session_factory: Callable[[], Session],
    settings: Settings,
    stop_event: asyncio.Event | None = None,
    *,
    media_queue: asyncio.Queue[int] | None = None,
) -> None:
    """
    后台扫描任务，定期扫描源目录并将新文件ID放入队列。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        settings: 应用配置对象
        media_queue: 用于放入新发现媒体文件ID的队列
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
                            settings, 
                            allowed_extensions
                        )
                
                # 使用 asyncio.to_thread 在线程池中执行同步操作
                new_file_ids = await asyncio.to_thread(_sync_scan)
                
                if new_file_ids:
                    logger.info(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描发现 {len(new_file_ids)} 个新文件")
                    
                    # 将新文件ID放入队列
                    if media_queue is not None:
                        for file_id in new_file_ids:
                            await media_queue.put(file_id)
                            logger.debug(f"{SCANNER_LOG_PREFIX} 文件ID {file_id} 已放入处理队列")
                    else:
                        logger.warning(f"{SCANNER_LOG_PREFIX} 媒体队列未提供，无法放入新文件ID")
                else:
                    logger.debug(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描未发现新文件")
                    
            except Exception as e:
                logger.error(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描失败: {e}")
            
            # 等待指定间隔或停止事件
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=settings.SCAN_INTERVAL_SECONDS,
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