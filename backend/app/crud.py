"""
数据库CRUD操作模块

提供数据库交互的封装函数，包括MediaFile模型的创建和查询操作。
使用SQLModel进行数据库操作，支持类型安全的ORM查询。
"""

from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from .core.models import MediaFile


def get_media_file_by_inode_device(
    db: Session, inode: int, device_id: int
) -> Optional[MediaFile]:
    """
    根据inode和device_id查询MediaFile记录。
    
    Args:
        db: 数据库会话
        inode: 文件的inode号
        device_id: 文件所在的设备ID
        
    Returns:
        Optional[MediaFile]: 匹配的MediaFile记录，如果不存在则返回None
    """
    statement = select(MediaFile).where(
        MediaFile.inode == inode,
        MediaFile.device_id == device_id
    )
    return db.exec(statement).first()


def create_media_file(db: Session, file_path: Path) -> MediaFile:
    """
    创建新的MediaFile记录。
    
    Args:
        db: 数据库会话
        file_path: 文件路径（Path对象）
        
    Returns:
        MediaFile: 创建的MediaFile记录
        
    Raises:
        OSError: 当文件不存在或无法访问时抛出
        ValueError: 当文件路径无效时抛出
    """
    # 验证文件是否存在
    if not file_path.exists():
        raise OSError(f"文件不存在: {file_path}")
    
    # 获取文件统计信息
    stat_info = file_path.stat()
    
    # 创建MediaFile实例
    media_file = MediaFile(
        inode=stat_info.st_ino,
        device_id=stat_info.st_dev,
        original_filepath=str(file_path.absolute()),
        original_filename=file_path.name,
        file_size=stat_info.st_size
    )
    
    # 添加到数据库会话
    db.add(media_file)
    db.commit()
    db.refresh(media_file)
    
    return media_file 