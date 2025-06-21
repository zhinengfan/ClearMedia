"""
API端点测试模块

测试ClearMedia API的各个端点，包括媒体文件查询、分页、筛选等功能。
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.models import MediaFile, FileStatus
from app.db import get_db


# 创建测试数据库引擎
@pytest.fixture(name="session")
def session_fixture():
    """创建测试用的数据库会话"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session


@pytest.fixture(name="mock_queue")
def mock_queue_fixture():
    """创建模拟的异步队列"""
    queue = AsyncMock()
    queue.put = AsyncMock()
    return queue


@pytest.fixture(name="client")
def client_fixture(session: Session, mock_queue, env_vars):
    """创建测试客户端，使用测试数据库和模拟队列"""
    # 延迟导入app，确保env_vars已设置
    from main import app  # noqa: WPS433

    def get_db_override():
        yield session

    app.dependency_overrides[get_db] = get_db_override
    
    # 设置模拟队列到app.state
    app.state.media_queue = mock_queue
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="sample_media_files")
def sample_media_files_fixture(session: Session):
    """创建测试用的媒体文件记录"""
    media_files = [
        MediaFile(
            inode=1001,
            device_id=2001,
            original_filepath="/test/movie1.mp4",
            original_filename="movie1.mp4",
            file_size=1000000,
            status=FileStatus.PENDING
        ),
        MediaFile(
            inode=1002,
            device_id=2001,
            original_filepath="/test/movie2.mkv",
            original_filename="movie2.mkv",
            file_size=2000000,
            status=FileStatus.COMPLETED
        ),
        MediaFile(
            inode=1003,
            device_id=2001,
            original_filepath="/test/tv_show.mp4",
            original_filename="tv_show.mp4",
            file_size=1500000,
            status=FileStatus.FAILED
        ),
        MediaFile(
            inode=1004,
            device_id=2001,
            original_filepath="/test/unknown.avi",
            original_filename="unknown.avi",
            file_size=800000,
            status=FileStatus.NO_MATCH
        ),
        MediaFile(
            inode=1005,
            device_id=2001,
            original_filepath="/test/processing.mp4",
            original_filename="processing.mp4",
            file_size=3000000,
            status=FileStatus.PROCESSING
        ),
    ]
    
    for media_file in media_files:
        session.add(media_file)
    session.commit()
    
    # 刷新对象以获取ID
    for media_file in media_files:
        session.refresh(media_file)
    
    return media_files


# 自动使用env_vars fixture以确保必需的环境变量存在
@pytest.fixture(autouse=True)
def _setup_env_vars(env_vars):
    """确保在所有测试之前设置必需的环境变量"""
    pass


class TestMediaFilesAPI:
    """测试媒体文件API端点"""
    
    def test_get_files_default_params(self, client: TestClient, sample_media_files):
        """测试默认参数的文件列表查询"""
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "items" in data
        
        assert data["total"] == 5
        assert data["skip"] == 0
        assert data["limit"] == 20
        assert len(data["items"]) == 5
    
    def test_get_files_with_limit(self, client: TestClient, sample_media_files):
        """测试带limit参数的查询"""
        response = client.get("/api/files?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert data["limit"] == 3
        assert len(data["items"]) == 3
    
    def test_get_files_with_skip(self, client: TestClient, sample_media_files):
        """测试带skip参数的查询（分页）"""
        response = client.get("/api/files?skip=2&limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert data["skip"] == 2
        assert data["limit"] == 2
        assert len(data["items"]) == 2
    
    def test_get_files_with_status_filter(self, client: TestClient, sample_media_files):
        """测试按状态筛选"""
        response = client.get(f"/api/files?status={FileStatus.PENDING}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.PENDING
    
    def test_get_files_with_completed_status(self, client: TestClient, sample_media_files):
        """测试查询COMPLETED状态的文件"""
        response = client.get(f"/api/files?status={FileStatus.COMPLETED}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.COMPLETED
    
    def test_get_files_with_no_match_status(self, client: TestClient, sample_media_files):
        """测试查询NO_MATCH状态的文件"""
        response = client.get(f"/api/files?status={FileStatus.NO_MATCH}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.NO_MATCH
    
    def test_get_files_invalid_status(self, client: TestClient, sample_media_files):
        """测试无效状态值"""
        response = client.get("/api/files?status=INVALID_STATUS")
        assert response.status_code == 422
        
        data = response.json()
        assert "无效的状态值" in data["detail"]
    
    def test_get_files_limit_too_large(self, client: TestClient, sample_media_files):
        """测试超出最大limit限制"""
        response = client.get("/api/files?limit=1000")
        assert response.status_code == 422
    
    def test_get_files_negative_skip(self, client: TestClient, sample_media_files):
        """测试负数skip值"""
        response = client.get("/api/files?skip=-1")
        assert response.status_code == 422
    
    def test_get_files_empty_database(self, client: TestClient):
        """测试空数据库"""
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    def test_get_files_order_by_created_at_desc(self, client: TestClient, sample_media_files):
        """测试结果按创建时间降序排列"""
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证时间戳是降序的（最新的在前）
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time >= next_time


class TestRetryAPI:
    """测试重试API端点"""
    
    def test_retry_failed_file_success(self, client: TestClient, sample_media_files, mock_queue, session: Session):
        """测试成功重试失败状态的文件"""
        # 找到FAILED状态的文件
        failed_file = next(f for f in sample_media_files if f.status == FileStatus.FAILED)
        
        response = client.post(f"/api/files/{failed_file.id}/retry")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "文件已成功排队重新处理"
        assert data["file_id"] == failed_file.id
        assert data["previous_status"] == FileStatus.FAILED
        assert data["current_status"] == FileStatus.PENDING
        
        # 验证队列被调用
        mock_queue.put.assert_called_once_with(failed_file.id)
        
        # 验证数据库状态已更新
        session.refresh(failed_file)
        assert failed_file.status == FileStatus.PENDING
    
    def test_retry_no_match_file_success(self, client: TestClient, sample_media_files, mock_queue, session: Session):
        """测试成功重试NO_MATCH状态的文件"""
        # 找到NO_MATCH状态的文件
        no_match_file = next(f for f in sample_media_files if f.status == FileStatus.NO_MATCH)
        
        response = client.post(f"/api/files/{no_match_file.id}/retry")
        assert response.status_code == 200
        
        data = response.json()
        assert data["previous_status"] == FileStatus.NO_MATCH
        assert data["current_status"] == FileStatus.PENDING
        
        # 验证队列被调用
        mock_queue.put.assert_called_once_with(no_match_file.id)
        
        # 验证数据库状态已更新
        session.refresh(no_match_file)
        assert no_match_file.status == FileStatus.PENDING
    
    def test_retry_nonexistent_file(self, client: TestClient, mock_queue):
        """测试重试不存在的文件"""
        response = client.post("/api/files/99999/retry")
        assert response.status_code == 404
        
        data = response.json()
        assert "媒体文件不存在" in data["detail"]
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
    
    def test_retry_completed_file_not_allowed(self, client: TestClient, sample_media_files, mock_queue):
        """测试重试已完成的文件（不允许）"""
        # 找到COMPLETED状态的文件
        completed_file = next(f for f in sample_media_files if f.status == FileStatus.COMPLETED)
        
        response = client.post(f"/api/files/{completed_file.id}/retry")
        assert response.status_code == 400
        
        data = response.json()
        assert "文件状态不允许重试" in data["detail"]
        assert FileStatus.COMPLETED in data["detail"]
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
    
    def test_retry_pending_file_not_allowed(self, client: TestClient, sample_media_files, mock_queue):
        """测试重试PENDING状态的文件（不允许）"""
        # 找到PENDING状态的文件
        pending_file = next(f for f in sample_media_files if f.status == FileStatus.PENDING)
        
        response = client.post(f"/api/files/{pending_file.id}/retry")
        assert response.status_code == 400
        
        data = response.json()
        assert "文件状态不允许重试" in data["detail"]
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
    
    def test_retry_processing_file_not_allowed(self, client: TestClient, sample_media_files, mock_queue):
        """测试重试PROCESSING状态的文件（不允许）"""
        # 找到PROCESSING状态的文件
        processing_file = next(f for f in sample_media_files if f.status == FileStatus.PROCESSING)
        
        response = client.post(f"/api/files/{processing_file.id}/retry")
        assert response.status_code == 400
        
        data = response.json()
        assert "文件状态不允许重试" in data["detail"]
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()


class TestStatsAPI:
    """测试统计API端点"""
    
    def test_get_stats_with_data(self, client: TestClient, sample_media_files):
        """测试有数据时的统计API"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证返回的统计数据
        expected_stats = {
            FileStatus.PENDING: 1,
            FileStatus.COMPLETED: 1,
            FileStatus.FAILED: 1,
            FileStatus.NO_MATCH: 1,
            FileStatus.PROCESSING: 1
        }
        
        assert data == expected_stats
    
    def test_get_stats_empty_database(self, client: TestClient):
        """测试空数据库时的统计API"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证返回空对象
        assert data == {}
    
    def test_get_stats_single_status(self, client: TestClient, session: Session):
        """测试只有单一状态的统计"""
        # 创建只有PENDING状态的文件
        media_files = [
            MediaFile(
                inode=2001,
                device_id=3001,
                original_filepath="/test/file1.mp4",
                original_filename="file1.mp4",
                file_size=1000000,
                status=FileStatus.PENDING
            ),
            MediaFile(
                inode=2002,
                device_id=3001,
                original_filepath="/test/file2.mp4",
                original_filename="file2.mp4",
                file_size=2000000,
                status=FileStatus.PENDING
            ),
        ]
        
        for media_file in media_files:
            session.add(media_file)
        session.commit()
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证只返回PENDING状态的统计
        expected_stats = {
            FileStatus.PENDING: 2
        }
        
        assert data == expected_stats
    
    def test_get_stats_multiple_same_status(self, client: TestClient, session: Session):
        """测试多个相同状态文件的统计"""
        # 创建多个FAILED状态的文件
        media_files = [
            MediaFile(
                inode=3001,
                device_id=4001,
                original_filepath="/test/failed1.mp4",
                original_filename="failed1.mp4",
                file_size=1000000,
                status=FileStatus.FAILED
            ),
            MediaFile(
                inode=3002,
                device_id=4001,
                original_filepath="/test/failed2.mp4",
                original_filename="failed2.mp4",
                file_size=2000000,
                status=FileStatus.FAILED
            ),
            MediaFile(
                inode=3003,
                device_id=4001,
                original_filepath="/test/failed3.mp4",
                original_filename="failed3.mp4",
                file_size=3000000,
                status=FileStatus.FAILED
            ),
        ]
        
        for media_file in media_files:
            session.add(media_file)
        session.commit()
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证FAILED状态有3个文件
        expected_stats = {
            FileStatus.FAILED: 3
        }
        
        assert data == expected_stats 