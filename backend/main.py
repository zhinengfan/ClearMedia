from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from loguru import logger
from app.config import settings, cleanup_deprecated_configs
from app.api import router as api_router, tags_metadata

import asyncio
from app.db import create_db_and_tables, get_session_factory
from app.services.media.scanner import background_scanner_task
from app.services.media.producer import producer_loop
from app.services.media.processor import process_media_file
from app.services.media.status_manager import set_processing

# 配置日志
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=settings.LOG_LEVEL.value,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "{extra} {message}"
)


async def worker_loop(
    worker_id: int,
    queue: asyncio.Queue[int],
    db_session_factory,
    settings
) -> None:
    """工作者协程循环
    
    从队列中获取文件 ID，将状态更新为 PROCESSING，然后处理文件。
    
    Args:
        worker_id: 工作者ID（用于日志标识）
        queue: 包含文件ID的异步队列
        db_session_factory: 数据库会话工厂
        settings: 应用配置
    """
    worker_logger = logger.bind(worker_id=worker_id)
    worker_logger.info(f"Worker-{worker_id} 启动")
    
    while True:
        try:
            # 从队列中获取文件 ID
            media_file_id = await queue.get()
            worker_logger.info(f"Worker-{worker_id} 获取到任务: media_file_id={media_file_id}")
            
            try:
                # 将状态从 QUEUED 更新为 PROCESSING
                set_processing(db_session_factory, media_file_id)
                worker_logger.info(f"Worker-{worker_id} 已将文件 {media_file_id} 状态更新为 PROCESSING")
                
                # 处理媒体文件
                result = await process_media_file(media_file_id, db_session_factory, settings)
                
                if result.success:
                    worker_logger.info(f"Worker-{worker_id} 成功处理文件 {media_file_id}")
                else:
                    worker_logger.warning(f"Worker-{worker_id} 处理文件 {media_file_id} 失败: {result.message}")
                    
            except Exception as e:
                worker_logger.error(f"Worker-{worker_id} 处理文件 {media_file_id} 时发生异常: {e}")
            finally:
                # 标记任务完成
                queue.task_done()
                
        except asyncio.CancelledError:
            worker_logger.info(f"Worker-{worker_id} 被取消")
            break
        except Exception as e:
            worker_logger.error(f"Worker-{worker_id} 发生异常: {e}")
            await asyncio.sleep(1)  # 避免快速循环


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("应用启动，开始初始化...")
    create_db_and_tables()
    logger.info("数据库和表初始化完成")
    
    # 清理数据库中的废弃配置项
    logger.info("开始清理废弃配置项...")
    cleanup_deprecated_configs()
    logger.info("废弃配置项清理完成")
    
    db_session_factory = get_session_factory()
    
    # 创建共享队列
    media_file_queue: asyncio.Queue[int] = asyncio.Queue()
    logger.info("创建媒体文件处理队列")
    
    # 将队列保存到app.state中，供API路由访问
    app.state.media_queue = media_file_queue
    logger.info("队列已保存到app.state.media_queue")
    
    # 启动后台任务
    background_tasks = []
    
    # 1. 启动 Scanner（不传递队列，仅负责扫描和入库）
    scanner_task = asyncio.create_task(
        background_scanner_task(
            db_session_factory=db_session_factory,
            settings=settings,
            stop_event=None,
            media_queue=None  # 重要：不传递队列
        )
    )
    scanner_task.set_name("scanner")
    background_tasks.append(scanner_task)
    logger.info("启动 Scanner 任务（仅负责扫描和入库）")
    
    # 2. 启动 Producer（负责从数据库获取 PENDING 文件并放入队列）
    producer_task = asyncio.create_task(
        producer_loop(
            db_session_factory=db_session_factory,
            queue=media_file_queue,
            batch_size=settings.PRODUCER_BATCH_SIZE,
            interval_seconds=settings.PRODUCER_INTERVAL_SECONDS
        )
    )
    producer_task.set_name("producer")
    background_tasks.append(producer_task)
    logger.info(f"启动 Producer 任务（批量大小: {settings.PRODUCER_BATCH_SIZE}, 间隔: {settings.PRODUCER_INTERVAL_SECONDS}秒）")
    
    # 3. 启动 Workers（从队列获取文件并处理）
    worker_tasks = []
    for i in range(settings.WORKER_COUNT):
        worker_task = asyncio.create_task(
            worker_loop(
                worker_id=i + 1,
                queue=media_file_queue,
                db_session_factory=db_session_factory,
                settings=settings
            )
        )
        worker_task.set_name(f"worker-{i+1}")
        worker_tasks.append(worker_task)
        background_tasks.append(worker_task)
        logger.info(f"启动 Worker-{i+1}")
    
    logger.info(f"所有后台任务启动完成 - Scanner: 1, Producer: 1, Workers: {settings.WORKER_COUNT}")
    
    yield
    
    # Shutdown
    logger.info("正在关闭所有后台任务...")
    
    # 取消所有后台任务
    for task in background_tasks:
        task.cancel()
    
    # 等待所有任务完成
    try:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"关闭任务时发生异常: {e}")
    
    logger.info("所有后台任务已关闭")


app = FastAPI(title="ClearMedia API", lifespan=lifespan, openapi_tags=tags_metadata)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 引入API路由
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to ClearMedia API"}
