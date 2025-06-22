from sqlmodel import create_engine, Session, SQLModel
from .config import settings
from typing import Callable

# 数据库文件路径
DATABASE_URL = settings.DATABASE_URL

# 创建数据库引擎
# connect_args 是 SQLite 特有的配置，允许多个线程共享同一个连接。
# 这对于 FastAPI 的后台任务和 API 请求在不同线程中访问数据库至关重要。
engine = create_engine(DATABASE_URL, echo=settings.SQLITE_ECHO, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """
    在应用启动时创建数据库文件和所有定义的表。
    """
    SQLModel.metadata.create_all(engine)

    # ------------------------------------------------------------------
    # 确保关键索引存在 (idempotent)
    # ------------------------------------------------------------------
    # 注意：SQLite 对表达式索引支持良好，可直接在 lower(original_filename) 上建索引

    index_statements = [
        # 对文件名做大小写不敏感索引，加速模糊搜索
        "CREATE INDEX IF NOT EXISTS idx_media_name_ci ON mediafile (lower(original_filename))"
    ]

    with engine.begin() as conn:
        for stmt in index_statements:
            conn.exec_driver_sql(stmt)

def get_db():
    """
    一个FastAPI依赖项，用于提供数据库会话。
    它确保在请求处理完成后，数据库会话能被正确关闭。
    """
    with Session(engine) as session:
        yield session 

# ---------------------------------------------------------------------------
#   通用会话工厂函数 (后台任务 / 单元测试 / 脚本均可复用)
# ---------------------------------------------------------------------------

def get_session_factory() -> Callable[[], Session]:
    """返回一个调用即得 `Session` 的工厂函数。

    与 FastAPI 依赖 `get_db()` 的区别：
    - `get_db()` 返回生成器，用于 `Depends`
    - 本函数直接返回 `lambda: Session(engine)`，方便普通函数或后台协程使用
    """

    return lambda: Session(engine) 