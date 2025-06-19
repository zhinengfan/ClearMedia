"""
processor.py 综合测试

使用 pytest-asyncio 和 monkeypatch 模拟 LLM、TMDB、Linker 依赖，
覆盖成功、LLM失败、TMDB失败、Linker失败、Linker冲突、禁用TMDB六个分支场景。
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from app.processor import process_media_file
from app.core.models import MediaFile, FileStatus
from app.core.linker import LinkResult
from app.config import Settings


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
def test_settings():
    """测试用配置"""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key",
        TMDB_API_KEY="test-key",
        SOURCE_DIR=Path("/tmp/test-source"),
        TARGET_DIR=Path("/tmp/test-target"),
        ENABLE_LLM=True,
        ENABLE_TMDB=True,
        WORKER_COUNT=1
    )


@pytest.fixture
def sample_media_file(db_session_factory):
    """创建示例媒体文件记录"""
    with db_session_factory() as session:
        # 直接创建 MediaFile 记录，不依赖实际文件
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


@pytest.mark.asyncio
async def test_process_media_file_success(
    monkeypatch,
    db_session_factory,
    test_settings,
    sample_media_file
):
    """测试成功处理分支：所有步骤都成功"""
    
    # 模拟 LLM 分析成功
    mock_llm_result = {
        "title": "Sample Movie",
        "year": 2023,
        "type": "movie"
    }
    mock_analyze_filename = AsyncMock(return_value=mock_llm_result)
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 模拟 TMDB 搜索成功
    mock_tmdb_result = {
        "tmdb_id": 12345,
        "media_type": "movie",
        "processed_data": {
            "title": "Sample Movie",
            "release_date": "2023-06-15",
            "overview": "A sample movie for testing"
        }
    }
    mock_search_media = AsyncMock(return_value=mock_tmdb_result)
    monkeypatch.setattr("app.core.tmdb.search_media", mock_search_media)
    
    # 模拟 Linker 成功
    mock_create_hardlink = MagicMock(return_value=LinkResult.LINK_SUCCESS)
    monkeypatch.setattr("app.processor.create_hardlink", mock_create_hardlink)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings)
    
    # 验证结果
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.COMPLETED
        assert updated_file.error_message is None
        assert updated_file.new_filepath is not None
        assert updated_file.processed_data is not None
        assert updated_file.processed_data["title"] == "Sample Movie"
    
    # 验证调用
    mock_analyze_filename.assert_called_once()
    mock_search_media.assert_called_once()
    mock_create_hardlink.assert_called_once()


@pytest.mark.asyncio
async def test_process_media_file_llm_failure(
    monkeypatch,
    db_session_factory,
    test_settings,
    sample_media_file
):
    """测试LLM失败分支：LLM分析抛出异常"""
    
    # 模拟 LLM 分析失败
    mock_analyze_filename = AsyncMock(side_effect=Exception("LLM API Error"))
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings)
    
    # 验证结果
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.FAILED
        assert "LLM API Error" in updated_file.error_message
        assert updated_file.processed_data is None
        assert updated_file.new_filepath is None


@pytest.mark.asyncio
async def test_process_media_file_tmdb_failure(
    monkeypatch,
    db_session_factory,
    test_settings,
    sample_media_file
):
    """测试TMDB失败分支：TMDB搜索抛出异常"""
    
    # 模拟 LLM 分析成功
    mock_llm_result = {
        "title": "Sample Movie",
        "year": 2023,
        "type": "movie"
    }
    mock_analyze_filename = AsyncMock(return_value=mock_llm_result)
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 模拟 TMDB 搜索失败
    mock_search_media = AsyncMock(side_effect=Exception("TMDB API Error"))
    monkeypatch.setattr("app.core.tmdb.search_media", mock_search_media)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings)
    
    # 验证结果
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.FAILED
        assert "TMDB API Error" in updated_file.error_message
        assert updated_file.processed_data is None
        assert updated_file.new_filepath is None


@pytest.mark.asyncio
async def test_process_media_file_linker_failure(
    monkeypatch,
    db_session_factory,
    test_settings,
    sample_media_file
):
    """测试Linker失败分支：硬链接创建失败"""
    
    # 模拟 LLM 分析成功
    mock_llm_result = {
        "title": "Sample Movie",
        "year": 2023,
        "type": "movie"
    }
    mock_analyze_filename = AsyncMock(return_value=mock_llm_result)
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 模拟 TMDB 搜索成功
    mock_tmdb_result = {
        "tmdb_id": 12345,
        "media_type": "movie",
        "processed_data": {
            "title": "Sample Movie",
            "release_date": "2023-06-15",
            "overview": "A sample movie for testing"
        }
    }
    mock_search_media = AsyncMock(return_value=mock_tmdb_result)
    monkeypatch.setattr("app.core.tmdb.search_media", mock_search_media)
    
    # 模拟 Linker 失败
    mock_create_hardlink = MagicMock(return_value=LinkResult.LINK_FAILED_UNKNOWN)
    monkeypatch.setattr("app.processor.create_hardlink", mock_create_hardlink)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings)
    
    # 验证结果
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.FAILED
        assert "硬链接创建失败" in updated_file.error_message
        # processed_data 应该包含数据，因为前面的步骤成功了
        assert updated_file.processed_data is not None
        assert updated_file.new_filepath is None


@pytest.mark.asyncio
async def test_process_media_file_linker_conflict(
    monkeypatch,
    db_session_factory,
    test_settings,
    sample_media_file
):
    """测试Linker冲突分支：硬链接返回conflict状态"""
    
    # 模拟 LLM 分析成功
    mock_llm_result = {
        "title": "Sample Movie",
        "year": 2023,
        "type": "movie"
    }
    mock_analyze_filename = AsyncMock(return_value=mock_llm_result)
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 模拟 TMDB 搜索成功
    mock_tmdb_result = {
        "tmdb_id": 12345,
        "media_type": "movie",
        "processed_data": {
            "title": "Sample Movie",
            "release_date": "2023-06-15",
            "overview": "A sample movie for testing"
        }
    }
    mock_search_media = AsyncMock(return_value=mock_tmdb_result)
    monkeypatch.setattr("app.core.tmdb.search_media", mock_search_media)
    
    # 模拟 Linker 冲突
    mock_create_hardlink = MagicMock(return_value=LinkResult.LINK_FAILED_CONFLICT)
    monkeypatch.setattr("app.processor.create_hardlink", mock_create_hardlink)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings)
    
    # 验证结果
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.CONFLICT
        assert "目标路径已存在" in updated_file.error_message
        assert updated_file.processed_data is not None
        assert updated_file.new_filepath is None


@pytest.mark.asyncio
async def test_process_media_file_tmdb_disabled(
    monkeypatch,
    db_session_factory,
    sample_media_file
):
    """测试TMDB禁用分支：ENABLE_TMDB=False时跳过TMDB调用"""
    
    # 设置TMDB禁用
    test_settings_tmdb_disabled = Settings(
        DATABASE_URL="sqlite:///:memory:",
        OPENAI_API_KEY="test-key",
        TMDB_API_KEY="test-key",
        SOURCE_DIR=Path("/tmp/test-source"),
        TARGET_DIR=Path("/tmp/test-target"),
        ENABLE_LLM=True,
        ENABLE_TMDB=False,  # 禁用TMDB
        WORKER_COUNT=1
    )
    
    # 模拟 LLM 分析成功
    mock_llm_result = {
        "title": "Sample Movie",
        "year": 2023,
        "type": "movie"
    }
    mock_analyze_filename = AsyncMock(return_value=mock_llm_result)
    monkeypatch.setattr("app.core.llm.analyze_filename", mock_analyze_filename)
    
    # 模拟 TMDB 搜索（不应被调用）
    mock_search_media = AsyncMock()
    monkeypatch.setattr("app.core.tmdb.search_media", mock_search_media)
    
    # 模拟 Linker 成功（但不会被调用，因为没有TMDB数据）
    mock_create_hardlink = MagicMock(return_value=LinkResult.LINK_SUCCESS)
    monkeypatch.setattr("app.processor.create_hardlink", mock_create_hardlink)
    
    # 执行处理
    await process_media_file(sample_media_file.id, db_session_factory, test_settings_tmdb_disabled)
    
    # 验证结果（TMDB禁用时，没有TMDB数据就不会进行链接操作）
    with db_session_factory() as session:
        updated_file = session.get(MediaFile, sample_media_file.id)
        assert updated_file.status == FileStatus.COMPLETED
        assert updated_file.error_message is None
        assert updated_file.llm_guess is not None  # 应该有LLM结果
        assert updated_file.processed_data is None  # 没有TMDB数据
        assert updated_file.new_filepath is None    # 没有链接操作
    
    # 验证TMDB未被调用
    mock_analyze_filename.assert_called_once()
    mock_search_media.assert_not_called()
    mock_create_hardlink.assert_not_called()  # 没有TMDB数据，不会调用链接 