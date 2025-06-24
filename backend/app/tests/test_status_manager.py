"""
status_manager.py 单元测试

测试状态管理的各种场景：设置处理中、完成、失败、冲突、无匹配等状态
"""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from app.core.models import MediaFile, FileStatus
from app.services.media.status_manager import (
    update_status,
    set_processing,
    set_queued,
    set_completed,
    set_failed,
    set_no_match,
    set_conflict
)


@pytest.fixture
def in_memory_db():
    """创建内存SQLite数据库用于测试"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session_factory(in_memory_db):
    """数据库会话工厂"""
    def _get_session():
        return Session(in_memory_db)
    return _get_session


@pytest.fixture
def sample_media_file(db_session_factory):
    """创建示例媒体文件记录"""
    with db_session_factory() as session:
        media_file = MediaFile(
            inode=123456,
            device_id=654321,
            original_filepath="/tmp/test-source/Sample Movie (2023).mkv",
            original_filename="Sample Movie (2023).mkv",
            file_size=1024 * 1024 * 100,  # 100MB
            status=FileStatus.PENDING
        )
        session.add(media_file)
        session.commit()
        session.refresh(media_file)
        return media_file


class TestUpdateStatus:
    """测试基础状态更新函数"""
    
    def test_update_status_basic(self, db_session_factory, sample_media_file):
        """测试基础状态更新"""
        update_status(
            db_session_factory,
            sample_media_file.id,
            status=FileStatus.PROCESSING,
            error_message=None
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.PROCESSING
            assert updated_file.error_message is None
    
    def test_update_status_with_error(self, db_session_factory, sample_media_file):
        """测试带错误消息的状态更新"""
        error_msg = "Test error message"
        update_status(
            db_session_factory,
            sample_media_file.id,
            status=FileStatus.FAILED,
            error_message=error_msg
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.FAILED
            assert updated_file.error_message == error_msg
    
    def test_update_status_with_extra_fields(self, db_session_factory, sample_media_file):
        """测试带额外字段的状态更新"""
        extra_fields = {
            "tmdb_id": 12345,
            "media_type": "movie",
            "new_filepath": "/target/Movie (2023).mkv"
        }
        
        update_status(
            db_session_factory,
            sample_media_file.id,
            status=FileStatus.COMPLETED,
            error_message=None,
            extra_fields=extra_fields
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.COMPLETED
            assert updated_file.tmdb_id == 12345
            assert updated_file.media_type == "movie"
            assert updated_file.new_filepath == "/target/Movie (2023).mkv"
    
    def test_update_status_nonexistent_file(self, db_session_factory):
        """测试更新不存在的文件状态"""
        # 应该不抛出异常，只是记录日志
        update_status(
            db_session_factory,
            99999,  # 不存在的ID
            status=FileStatus.FAILED,
            error_message="Test error"
        )


class TestSetProcessing:
    """测试设置处理中状态"""
    
    def test_set_processing(self, db_session_factory, sample_media_file):
        """测试设置为处理中状态"""
        set_processing(db_session_factory, sample_media_file.id)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.PROCESSING
            assert updated_file.error_message is None


class TestSetQueued:
    """测试设置队列中状态"""
    
    def test_set_queued(self, db_session_factory, sample_media_file):
        """测试设置为队列中状态"""
        set_queued(db_session_factory, sample_media_file.id)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.QUEUED
            assert updated_file.error_message is None


class TestSetCompleted:
    """测试设置完成状态"""
    
    def test_set_completed_minimal(self, db_session_factory, sample_media_file):
        """测试最小参数的完成状态设置"""
        set_completed(db_session_factory, sample_media_file.id)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.COMPLETED
            assert updated_file.error_message is None
    
    def test_set_completed_full(self, db_session_factory, sample_media_file):
        """测试完整参数的完成状态设置"""
        set_completed(
            db_session_factory,
            sample_media_file.id,
            new_filepath="/target/Movie (2023).mkv",
            llm_guess={"title": "Movie", "year": 2023},
            tmdb_id=12345,
            media_type="movie",
            processed_data={"title": "Movie", "release_date": "2023-01-01"}
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.COMPLETED
            assert updated_file.new_filepath == "/target/Movie (2023).mkv"
            assert updated_file.llm_guess == {"title": "Movie", "year": 2023}
            assert updated_file.tmdb_id == 12345
            assert updated_file.media_type == "movie"
            assert updated_file.processed_data == {"title": "Movie", "release_date": "2023-01-01"}


class TestSetFailed:
    """测试设置失败状态"""
    
    def test_set_failed_basic(self, db_session_factory, sample_media_file):
        """测试基础失败状态设置"""
        error_msg = "Processing failed"
        set_failed(db_session_factory, sample_media_file.id, error_msg)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.FAILED
            assert updated_file.error_message == error_msg
    
    def test_set_failed_with_partial_data(self, db_session_factory, sample_media_file):
        """测试带部分数据的失败状态设置"""
        error_msg = "TMDB search failed"
        set_failed(
            db_session_factory,
            sample_media_file.id,
            error_msg,
            llm_guess={"title": "Movie", "year": 2023},
            tmdb_id=12345
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.FAILED
            assert updated_file.error_message == error_msg
            assert updated_file.llm_guess == {"title": "Movie", "year": 2023}
            assert updated_file.tmdb_id == 12345


class TestSetNoMatch:
    """测试设置无匹配状态"""
    
    def test_set_no_match(self, db_session_factory, sample_media_file):
        """测试设置无匹配状态"""
        set_no_match(db_session_factory, sample_media_file.id)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.NO_MATCH
            assert updated_file.error_message == "No TMDB match found"
    
    def test_set_no_match_with_llm_data(self, db_session_factory, sample_media_file):
        """测试带LLM数据的无匹配状态设置"""
        llm_guess = {"title": "Unknown Movie", "year": 2023}
        set_no_match(
            db_session_factory,
            sample_media_file.id,
            llm_guess=llm_guess
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.NO_MATCH
            assert updated_file.error_message == "No TMDB match found"
            assert updated_file.llm_guess == llm_guess


class TestSetConflict:
    """测试设置冲突状态"""
    
    def test_set_conflict_basic(self, db_session_factory, sample_media_file):
        """测试基础冲突状态设置"""
        conflict_path = "/target/Movie (2023).mkv"
        set_conflict(db_session_factory, sample_media_file.id, conflict_path)
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.CONFLICT
            assert f"目标路径已存在: {conflict_path}" in updated_file.error_message
    
    def test_set_conflict_with_full_data(self, db_session_factory, sample_media_file):
        """测试带完整数据的冲突状态设置"""
        conflict_path = "/target/Movie (2023).mkv"
        set_conflict(
            db_session_factory,
            sample_media_file.id,
            conflict_path,
            llm_guess={"title": "Movie", "year": 2023},
            tmdb_id=12345,
            media_type="movie",
            processed_data={"title": "Movie", "release_date": "2023-01-01"}
        )
        
        with db_session_factory() as session:
            updated_file = session.get(MediaFile, sample_media_file.id)
            assert updated_file.status == FileStatus.CONFLICT
            assert f"目标路径已存在: {conflict_path}" in updated_file.error_message
            assert updated_file.llm_guess == {"title": "Movie", "year": 2023}
            assert updated_file.tmdb_id == 12345
            assert updated_file.media_type == "movie"
            assert updated_file.processed_data == {"title": "Movie", "release_date": "2023-01-01"} 