from fastapi import FastAPI
from contextlib import asynccontextmanager

from loguru import logger
from app.config import settings

import asyncio


from app.db import create_db_and_tables, get_session_factory
from app.processor import process_media_file
from app.scanner import background_scanner_task

# 配置日志
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=settings.LOG_LEVEL.value,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "{extra} {message}"
)

# 全局队列，用于 scanner 和 processor 之间的解耦
media_file_queue: asyncio.Queue[int] = asyncio.Queue()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("应用启动，开始初始化...")
    create_db_and_tables()
    logger.info("数据库和表初始化完成")
    db_session_factory = get_session_factory()
    
    async def worker() -> None:
        """工作者协程，从队列中获取媒体文件ID并处理"""
        while True:
            try:
                # 从队列中获取媒体文件ID
                media_id = await media_file_queue.get()
                logger.info(f"工作者获取到任务: media_id={media_id}")
                
                try:
                    await process_media_file(media_id, db_session_factory, settings)
                except Exception as e:
                    logger.error(f"处理媒体文件 {media_id} 失败: {e}")
                finally:
                    # 标记任务完成
                    media_file_queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info("工作者协程被取消")
                break
            except Exception as e:
                logger.error(f"工作者协程异常: {e}")
                await asyncio.sleep(1)  # 避免快速循环
    
    # 创建多个工作者协程
    worker_tasks = []
    for i in range(settings.WORKER_COUNT):
        task = asyncio.create_task(worker())
        task.set_name(f"worker-{i+1}")
        worker_tasks.append(task)
        logger.info(f"启动工作者协程 {i+1}/{settings.WORKER_COUNT}")
    
    # 启动后台扫描任务
    scanner_task = asyncio.create_task(
        background_scanner_task(db_session_factory, settings, media_queue=media_file_queue)
    )
    scanner_task.set_name("scanner")
    logger.info("启动后台扫描任务")
    
    yield
    
    # Shutdown
    logger.info("正在关闭所有后台任务...")
    
    # 取消扫描任务
    scanner_task.cancel()
    
    # 取消所有工作者任务
    for task in worker_tasks:
        task.cancel()
    
    # 等待所有任务完成
    all_tasks = [scanner_task] + worker_tasks
    try:
        await asyncio.gather(*all_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"关闭任务时发生异常: {e}")
    
    logger.info("所有后台任务已关闭")

app = FastAPI(title="ClearMedia API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Welcome to ClearMedia API"}
