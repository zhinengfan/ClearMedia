import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, JSON, Column


def utc_now() -> datetime.datetime:
    """获取当前UTC时间，用于数据库时间戳"""
    return datetime.datetime.now(datetime.timezone.utc)

# 定义文件状态的枚举值，便于管理和引用
class FileStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CONFLICT = "CONFLICT"
    NO_MATCH = "NO_MATCH"

class MediaFile(SQLModel, table=True):
    """
    代表一个被扫描到的媒体文件及其处理状态。
    """
    # 基础信息
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime.datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime.datetime = Field(default_factory=utc_now, nullable=False, sa_column_kwargs={"onupdate": utc_now})

    # --------------------------------------------------------------------------
    # 文件唯一标识 (关键字段，用于去重)
    # --------------------------------------------------------------------------
    inode: int = Field(index=True, nullable=False, description="文件的inode号，用于在同一设备内唯一标识文件内容")
    device_id: int = Field(index=True, nullable=False, description="文件所在的设备ID")

    # 原始文件信息
    original_filepath: str = Field(index=True, nullable=False, description="文件的原始绝对路径")
    original_filename: str = Field(nullable=False, description="原始文件名")
    file_size: int = Field(nullable=False, description="文件大小（字节）")

    # --------------------------------------------------------------------------
    # 状态与处理流程管理 (核心逻辑驱动字段)
    # --------------------------------------------------------------------------
    status: str = Field(
        default=FileStatus.PENDING, 
        index=True, 
        nullable=False,
        description=f"文件当前处理状态: {FileStatus.PENDING}, {FileStatus.PROCESSING}, {FileStatus.COMPLETED}, {FileStatus.FAILED}, {FileStatus.CONFLICT}, {FileStatus.NO_MATCH}"
    )
    
    # --------------------------------------------------------------------------
    # 识别与处理结果
    # --------------------------------------------------------------------------
    # LLM处理结果
    llm_guess: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="LLM分析后返回的原始JSON对象")

    # TMDB处理结果
    tmdb_id: Optional[int] = Field(default=None, index=True, description="从TMDB匹配到的最终媒体ID")
    media_type: Optional[str] = Field(default=None, description="媒体类型: 'movie' 或 'tv'")
    
    # 最终用于重命名的结构化数据
    processed_data: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="从TMDB获取并整理好的、用于重命名的最终数据")
    
    # 新文件路径
    new_filepath: Optional[str] = Field(default=None, index=True, description="成功创建硬链接后的新文件绝对路径")
    
    # --------------------------------------------------------------------------
    # 错误与重试管理
    # --------------------------------------------------------------------------
    # 记录详细的失败原因，便于调试
    error_message: Optional[str] = Field(default=None, description="记录最后一次失败的原因")
    
    # 重试次数计数器
    retry_count: int = Field(default=0, nullable=False, description="当前重试次数") 


class ConfigItem(SQLModel, table=True):
    """
    存储应用配置项的数据库模型。
    支持动态配置管理，配置值以JSON格式存储，支持复杂数据结构。
    """
    # 配置项的唯一标识符，作为主键
    key: str = Field(primary_key=True, nullable=False, description="配置项的唯一键名")
    
    # 配置值，以JSON字符串格式存储，支持各种数据类型
    value: str = Field(nullable=False, description="配置项的值，以JSON序列化字符串存储")
    
    # 配置项的可选描述说明
    description: Optional[str] = Field(default=None, description="配置项的描述说明")
    
    # 最后更新时间，自动维护
    updated_at: datetime.datetime = Field(
        default_factory=utc_now, 
        nullable=False, 
        sa_column_kwargs={"onupdate": utc_now},
        description="配置项最后更新时间"
    ) 