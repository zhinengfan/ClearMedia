"""
CRUD模块的单元测试

使用内存SQLite数据库进行真实的数据库操作测试，
确保get_media_file_by_inode_device和create_media_file函数的正确性。
"""

import tempfile
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.models import MediaFile
from app.crud import create_media_file, get_media_file_by_inode_device


@pytest.fixture
def in_memory_db():
    """
    创建内存SQLite数据库的pytest fixture。
    
    每个测试使用独立的内存数据库，测试完成后自动清理。
    """
    # 创建内存数据库引擎
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,  # 测试时不输出SQL语句
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    SQLModel.metadata.create_all(engine)
    
    # 创建数据库会话
    with Session(engine) as session:
        yield session


@pytest.fixture
def temp_file():
    """
    创建临时文件的pytest fixture。
    
    Returns:
        Path: 临时文件的路径
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(b"test content")
        temp_path = Path(tmp_file.name)
    
    yield temp_path
    
    # 清理临时文件
    if temp_path.exists():
        temp_path.unlink()


class TestCreateMediaFile:
    """测试create_media_file函数"""
    
    def test_create_media_file_success(self, in_memory_db: Session, temp_file: Path):
        """测试成功创建MediaFile记录"""
        # 执行创建操作
        media_file = create_media_file(in_memory_db, temp_file)
        
        # 验证返回的对象
        assert media_file is not None
        assert media_file.id is not None  # 应该有自动生成的ID
        assert media_file.original_filepath == str(temp_file.absolute())
        assert media_file.original_filename == temp_file.name
        assert media_file.file_size > 0  # 文件应该有内容
        assert media_file.inode > 0  # inode应该是正数
        assert media_file.device_id is not None  # device_id应该存在
        
        # 验证数据库中确实存在该记录
        db_media_file = in_memory_db.get(MediaFile, media_file.id)
        assert db_media_file is not None
        assert db_media_file.original_filepath == media_file.original_filepath
    
    def test_create_media_file_nonexistent_file(self, in_memory_db: Session):
        """测试创建不存在文件的MediaFile记录应该抛出异常"""
        nonexistent_path = Path("/path/that/does/not/exist.mp4")
        
        with pytest.raises(OSError, match="文件不存在"):
            create_media_file(in_memory_db, nonexistent_path)


class TestGetMediaFileByInodeDevice:
    """测试get_media_file_by_inode_device函数"""
    
    def test_get_existing_media_file(self, in_memory_db: Session, temp_file: Path):
        """测试获取已存在的MediaFile记录"""
        # 先创建一个MediaFile记录
        created_media_file = create_media_file(in_memory_db, temp_file)
        
        # 使用inode和device_id查询
        found_media_file = get_media_file_by_inode_device(
            in_memory_db,
            created_media_file.inode,
            created_media_file.device_id
        )
        
        # 验证找到的记录
        assert found_media_file is not None
        assert found_media_file.id == created_media_file.id
        assert found_media_file.original_filepath == created_media_file.original_filepath
        assert found_media_file.inode == created_media_file.inode
        assert found_media_file.device_id == created_media_file.device_id
    
    def test_get_nonexistent_media_file(self, in_memory_db: Session):
        """测试获取不存在的MediaFile记录应该返回None"""
        # 使用不存在的inode和device_id查询
        found_media_file = get_media_file_by_inode_device(
            in_memory_db,
            inode=999999,
            device_id=999999
        )
        
        # 应该返回None
        assert found_media_file is None


class TestCrudIntegration:
    """CRUD功能集成测试"""
    
    def test_create_and_retrieve_cycle(self, in_memory_db: Session, temp_file: Path):
        """测试创建-查询的完整周期"""
        # 1. 创建MediaFile记录
        created_media_file = create_media_file(in_memory_db, temp_file)
        assert created_media_file is not None
        
        # 2. 使用inode和device_id查询刚创建的记录
        retrieved_media_file = get_media_file_by_inode_device(
            in_memory_db,
            created_media_file.inode,
            created_media_file.device_id
        )
        
        # 3. 验证查询结果与创建的记录一致
        assert retrieved_media_file is not None
        assert retrieved_media_file.id == created_media_file.id
        assert retrieved_media_file.original_filepath == created_media_file.original_filepath
        assert retrieved_media_file.original_filename == created_media_file.original_filename
        assert retrieved_media_file.file_size == created_media_file.file_size
        assert retrieved_media_file.inode == created_media_file.inode
        assert retrieved_media_file.device_id == created_media_file.device_id
    
    def test_multiple_files_different_inodes(self, in_memory_db: Session):
        """测试多个不同文件的inode唯一性"""
        temp_files = []
        media_files = []
        
        try:
            # 创建多个临时文件
            for i in range(3):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.mp4") as tmp_file:
                    tmp_file.write(f"test content {i}".encode())
                    temp_path = Path(tmp_file.name)
                    temp_files.append(temp_path)
                    
                    # 为每个文件创建MediaFile记录
                    media_file = create_media_file(in_memory_db, temp_path)
                    media_files.append(media_file)
            
            # 验证每个文件都有不同的inode（在大多数文件系统中）
            inodes = [mf.inode for mf in media_files]
            assert len(set(inodes)) == len(inodes), "每个文件应该有唯一的inode"
            
            # 验证可以通过各自的inode和device_id查询到对应的记录
            for media_file in media_files:
                retrieved = get_media_file_by_inode_device(
                    in_memory_db,
                    media_file.inode,
                    media_file.device_id
                )
                assert retrieved is not None
                assert retrieved.id == media_file.id
        
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink() 