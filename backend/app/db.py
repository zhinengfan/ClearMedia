from sqlmodel import create_engine, Session, SQLModel
from app.config import settings

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

def get_db():
    """
    一个FastAPI依赖项，用于提供数据库会话。
    它确保在请求处理完成后，数据库会话能被正确关闭。
    """
    with Session(engine) as session:
        yield session 