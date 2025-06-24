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


def _parse_video_extensions(exts: str) -> set[str]:
    """
    解析视频扩展名字符串，返回标准化的扩展名集合。
    
    Args:
        exts: 逗号分隔的扩展名字符串（如 "mp4,mkv,avi" 或 ".mp4, .mkv"）
        
    Returns:
        set[str]: 标准化的扩展名集合，全部小写且以"."开头（如 {'.mp4', '.mkv', '.avi'}）
    """
    if not exts:
        return set()
    
    result = set()
    for part in exts.split(','):
        part = part.strip().lower()
        if part:  # 跳过空字符串
            if not part.startswith('.'):
                part = f'.{part}'
            result.add(part)
    
    return result


def _validate_file(
    file_path: Path,
    allowed_extensions: set[str],
    *,
    min_size_bytes: int
) -> tuple[bool, str]:
    """
    验证文件是否符合扩展名和大小要求。
    
    Args:
        file_path: 要验证的文件路径
        allowed_extensions: 允许的扩展名集合（如 {'.mp4', '.mkv'}）
        min_size_bytes: 最小文件大小（字节），0表示不检查大小
        
    Returns:
        tuple[bool, str]: (是否有效, 失败原因)
    """
    # 检查文件扩展名
    file_extension = file_path.suffix.lower()
    if file_extension not in allowed_extensions:
        return False, f"扩展名 {file_extension} 不在允许列表中"
    
    # 获取文件信息
    try:
        stat_info = file_path.stat()
    except OSError:
        return False, "无法获取文件信息"
    
    # 检查文件大小（仅当 min_size_bytes > 0 时）
    if min_size_bytes > 0 and stat_info.st_size < min_size_bytes:
        return False, f"文件大小 {stat_info.st_size} 字节小于最小要求 {min_size_bytes} 字节"
    
    return True, ""


def _process_single_file(
    db_session: Session,
    file_path: Path
) -> int | None:
    """
    处理单个文件，将其添加到数据库中（如果不存在）。
    
    Args:
        db_session: 数据库会话
        file_path: 要处理的文件路径
        
    Returns:
        int | None: 成功创建新记录时返回文件ID，其他情况返回None
    """
    # 获取文件的统计信息
    try:
        stat_info = file_path.stat()
    except OSError:
        return None
    
    inode = stat_info.st_ino
    device_id = stat_info.st_dev
    
    # 检查文件是否已存在于数据库中
    try:
        existing_media_file = crud.get_media_file_by_inode_device(
            db_session, inode, device_id
        )
    except Exception:
        return None
    
    # 如果文件已存在，返回None
    if existing_media_file is not None:
        return None
    
    # 如果文件不存在于数据库中，创建新记录
    try:
        new_media_file = crud.create_media_file(db_session, file_path)
        return new_media_file.id
    except Exception:
        return None


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
            # 跳过目标目录以提高效率
            # 使用resolve()确保路径是绝对的，然后用字符串比较
            if settings.SCAN_EXCLUDE_TARGET_DIR and str(Path(dirpath).resolve()).startswith(target_dir_abs):
                logger.trace(f"{SCANNER_LOG_PREFIX} 跳过目标目录及其子目录: {dirpath}")
                # 清空dirnames, 告诉os.walk不要再进入这个目录的子目录
                dirnames[:] = []
                continue

            for filename in filenames:
                files_found += 1
                file_path = Path(dirpath) / filename
            
                # 使用工具函数验证文件
                is_valid, reason = _validate_file(
                    file_path, 
                    allowed_extensions, 
                    min_size_bytes=min_file_size_bytes
                )
                
                if not is_valid:
                    logger.trace(f"{SCANNER_LOG_PREFIX} 跳过文件 {file_path.name}: {reason}")
                    continue
                
                # 使用工具函数处理文件
                new_file_id = _process_single_file(db_session, file_path)
                
                if new_file_id is not None:
                    new_file_ids.append(new_file_id)
                    logger.info(f"{SCANNER_LOG_PREFIX} 新增媒体文件: {file_path.name} (ID: {new_file_id})")
                else:
                    logger.trace(f"{SCANNER_LOG_PREFIX} 文件已存在于数据库或处理失败: {file_path.name}")
        
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
    allowed_extensions = _parse_video_extensions(settings.VIDEO_EXTENSIONS)
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
                    
                    # 将新文件ID放入队列（仅当提供了队列时）
                    if media_queue is not None:
                        for file_id in new_file_ids:
                            await media_queue.put(file_id)
                            logger.debug(f"{SCANNER_LOG_PREFIX} 文件ID {file_id} 已放入处理队列")
                    else:
                        logger.debug(f"{SCANNER_LOG_PREFIX} 媒体队列未提供，新文件仅存储到数据库")
                else:
                    logger.debug(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描未发现新文件")
                    
            except Exception as e:
                logger.error(f"{SCANNER_LOG_PREFIX} 第 {scan_count} 次扫描失败: {e}")
            
            # 等待指定间隔，同时检查停止事件
            await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)
                
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