"""媒体文件 Producer 模块

负责定期从数据库中查询待处理的媒体文件，并将它们放入队列供 Worker 处理。
Producer 使用批量查询和原子事务来确保并发安全性。
"""

import asyncio
from typing import Callable
from sqlmodel import Session, select
from loguru import logger

from ...core.models import MediaFile, FileStatus


async def producer_loop(
    db_session_factory: Callable[[], Session],
    queue: asyncio.Queue,
    batch_size: int,
    interval_seconds: int
) -> None:
    """Producer 主循环
    
    定期从数据库中查询待处理的媒体文件，将状态从 PENDING 更新为 QUEUED，
    并将文件 ID 放入队列供 Worker 处理。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        queue: 异步队列，用于向 Worker 传递待处理的文件 ID
        batch_size: 每次处理的最大文件数量
        interval_seconds: 轮询间隔时间（秒）
    """
    logger.info(f"Producer 启动，批量大小: {batch_size}, 轮询间隔: {interval_seconds}秒")
    
    while True:
        try:
            # 执行一次批量处理
            processed_count = await _process_batch(db_session_factory, queue, batch_size)
            
            if processed_count > 0:
                logger.info(f"Producer 处理了 {processed_count} 个文件")
            
            # 等待下一次轮询
            await asyncio.sleep(interval_seconds)
            
        except Exception as e:
            logger.error(f"Producer 循环出错: {e}")
            # 出错后等待更长时间再重试
            await asyncio.sleep(interval_seconds * 2)


async def _process_batch(
    db_session_factory: Callable[[], Session],
    queue: asyncio.Queue,
    batch_size: int
) -> int:
    """处理一批待处理的文件
    
    使用数据库事务和行级锁确保并发安全性。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        queue: 异步队列
        batch_size: 批量大小
        
    Returns:
        实际处理的文件数量
    """
    try:
        # 在线程池中执行数据库操作，获取文件 ID
        file_ids = await asyncio.to_thread(_sync_get_and_update_files, db_session_factory, batch_size)
        
        # 在主线程中将文件 ID 放入队列
        for file_id in file_ids:
            await queue.put(file_id)
        
        if file_ids:
            logger.debug(f"成功将 {len(file_ids)} 个文件状态更新为 QUEUED 并放入队列")
        
        return len(file_ids)
        
    except Exception as e:
        logger.error(f"批量处理文件时出错: {e}")
        return 0


def _sync_get_and_update_files(
    db_session_factory: Callable[[], Session],
    batch_size: int
) -> list[int]:
    """同步版本的文件获取和更新函数
    
    这个函数在线程池中运行，处理数据库事务，返回更新后的文件 ID 列表。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        batch_size: 批量大小
        
    Returns:
        更新后的文件 ID 列表
    """
    with db_session_factory() as session:
        try:
            # 使用 FOR UPDATE 锁定行，防止并发冲突
            # 查询 PENDING 状态的文件，限制数量，并加锁
            statement = (
                select(MediaFile)
                .where(MediaFile.status == FileStatus.PENDING)
                .limit(batch_size)
                .with_for_update()  # 行级锁
            )
            
            pending_files = session.exec(statement).all()
            
            if not pending_files:
                return []
            
            # 批量更新状态为 QUEUED
            file_ids = []
            for media_file in pending_files:
                media_file.status = FileStatus.QUEUED
                file_ids.append(media_file.id)
            
            # 提交事务
            session.commit()
            
            return file_ids
            
        except Exception as e:
            # 回滚事务
            session.rollback()
            logger.error(f"批量处理事务失败: {e}")
            raise


async def producer_single_run(
    db_session_factory: Callable[[], Session],
    queue: asyncio.Queue,
    batch_size: int
) -> int:
    """Producer 单次运行
    
    用于测试或手动触发，执行一次批量处理。
    
    Args:
        db_session_factory: 数据库会话工厂函数
        queue: 异步队列
        batch_size: 批量大小
        
    Returns:
        实际处理的文件数量
    """
    return await _process_batch(db_session_factory, queue, batch_size) 