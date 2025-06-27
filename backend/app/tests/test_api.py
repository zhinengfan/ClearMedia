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
    from main import app

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
        MediaFile(
            inode=1006,
            device_id=2001,
            original_filepath="/test/queued.mp4",
            original_filename="queued.mp4",
            file_size=2500000,
            status=FileStatus.QUEUED
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
        
        assert data["total"] == 6  # 现在包含QUEUED状态文件
        assert data["skip"] == 0
        assert data["limit"] == 20
        assert len(data["items"]) == 6
    
    def test_get_files_with_limit(self, client: TestClient, sample_media_files):
        """测试带limit参数的查询"""
        response = client.get("/api/files?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 现在包含QUEUED状态文件
        assert data["limit"] == 3
        assert len(data["items"]) == 3
    
    def test_get_files_with_skip(self, client: TestClient, sample_media_files):
        """测试带skip参数的查询（分页）"""
        response = client.get("/api/files?skip=2&limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 现在包含QUEUED状态文件
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

    def test_get_files_with_queued_status(self, client: TestClient, sample_media_files):
        """测试QUEUED状态筛选"""
        response = client.get(f"/api/files?status={FileStatus.QUEUED}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1  # 现在包含一个QUEUED状态文件
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.QUEUED
    
    def test_get_files_with_multiple_statuses(self, client: TestClient, sample_media_files):
        """测试多状态筛选（逗号分隔）"""
        response = client.get(f"/api/files?status={FileStatus.PENDING},{FileStatus.COMPLETED}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # PENDING 和 COMPLETED 各有一个
        assert len(data["items"]) == 2
        
        # 验证返回的都是指定状态
        returned_statuses = {item["status"] for item in data["items"]}
        assert returned_statuses == {FileStatus.PENDING, FileStatus.COMPLETED}
    
    def test_get_files_with_all_statuses(self, client: TestClient, sample_media_files):
        """测试筛选所有状态"""
        all_statuses = f"{FileStatus.PENDING},{FileStatus.QUEUED},{FileStatus.PROCESSING},{FileStatus.COMPLETED},{FileStatus.FAILED},{FileStatus.CONFLICT},{FileStatus.NO_MATCH}"
        response = client.get(f"/api/files?status={all_statuses}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 所有6个测试文件
        assert len(data["items"]) == 6
    
    def test_get_files_with_status_case_insensitive(self, client: TestClient, sample_media_files):
        """测试状态筛选不区分大小写"""
        response = client.get("/api/files?status=pending,completed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # PENDING 和 COMPLETED 各有一个
        assert len(data["items"]) == 2
        
        # 验证返回的都是指定状态（大写）
        returned_statuses = {item["status"] for item in data["items"]}
        assert returned_statuses == {FileStatus.PENDING, FileStatus.COMPLETED}
    
    def test_get_files_with_duplicate_statuses(self, client: TestClient, sample_media_files):
        """测试重复状态自动去重"""
        response = client.get(f"/api/files?status={FileStatus.PENDING},{FileStatus.PENDING},{FileStatus.COMPLETED}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # 应该去重，只返回 PENDING 和 COMPLETED
        assert len(data["items"]) == 2
        
        returned_statuses = {item["status"] for item in data["items"]}
        assert returned_statuses == {FileStatus.PENDING, FileStatus.COMPLETED}
    
    def test_get_files_with_empty_status_values(self, client: TestClient, sample_media_files):
        """测试空状态值和空白状态值"""
        # 测试完全空的状态参数
        response = client.get("/api/files?status=")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6  # 应该返回所有文件
        
        # 测试包含空白的状态参数
        response = client.get(f"/api/files?status=,{FileStatus.PENDING}, ,{FileStatus.COMPLETED},")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # 应该只返回有效的 PENDING 和 COMPLETED
        assert len(data["items"]) == 2
        
        returned_statuses = {item["status"] for item in data["items"]}
        assert returned_statuses == {FileStatus.PENDING, FileStatus.COMPLETED}
    
    def test_get_files_invalid_status(self, client: TestClient, sample_media_files):
        """测试无效状态值"""
        response = client.get("/api/files?status=INVALID_STATUS")
        assert response.status_code == 422
        
        data = response.json()
        assert "不支持的状态值" in data["detail"]
        assert "INVALID_STATUS" in data["detail"]
    
    def test_get_files_mixed_valid_invalid_statuses(self, client: TestClient, sample_media_files):
        """测试混合有效和无效状态值"""
        response = client.get(f"/api/files?status={FileStatus.PENDING},INVALID_STATUS,{FileStatus.COMPLETED}")
        assert response.status_code == 422
        
        data = response.json()
        assert "不支持的状态值" in data["detail"]
        assert "INVALID_STATUS" in data["detail"]
    
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

    def test_get_files_search_by_filename(self, client: TestClient, sample_media_files):
        """测试按文件名搜索"""
        response = client.get("/api/files?search=movie")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # movie1.mp4 和 movie2.mkv
        assert len(data["items"]) == 2
        
        # 验证搜索结果包含关键词
        for item in data["items"]:
            assert "movie" in item["original_filename"].lower()
    
    def test_get_files_search_by_filepath(self, client: TestClient, sample_media_files):
        """测试按文件路径搜索"""
        response = client.get("/api/files?search=/test/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 所有文件都在/test/目录下，现在包含QUEUED状态文件
        assert len(data["items"]) == 6
    
    def test_get_files_search_case_insensitive(self, client: TestClient, sample_media_files):
        """测试搜索大小写不敏感"""
        response = client.get("/api/files?search=MOVIE")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # 应该找到movie1.mp4和movie2.mkv
        assert len(data["items"]) == 2
    
    def test_get_files_search_no_results(self, client: TestClient, sample_media_files):
        """测试搜索无结果"""
        response = client.get("/api/files?search=nonexistent")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
    
    def test_get_files_search_empty_string(self, client: TestClient, sample_media_files):
        """测试空字符串搜索"""
        response = client.get("/api/files?search=")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 空搜索应该返回所有结果，现在包含QUEUED状态文件
        assert len(data["items"]) == 6
    
    def test_get_files_search_whitespace_only(self, client: TestClient, sample_media_files):
        """测试只包含空格的搜索"""
        response = client.get("/api/files?search=   ")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 6  # 只有空格的搜索应该返回所有结果，现在包含QUEUED状态文件
        assert len(data["items"]) == 6
    
    def test_get_files_sort_created_at_asc(self, client: TestClient, sample_media_files):
        """测试按创建时间升序排序"""
        response = client.get("/api/files?sort=created_at:asc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证时间戳是升序的（最早的在前）
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time <= next_time
    
    def test_get_files_sort_created_at_desc(self, client: TestClient, sample_media_files):
        """测试按创建时间降序排序（默认行为）"""
        response = client.get("/api/files?sort=created_at:desc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证时间戳是降序的（最新的在前）
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time >= next_time
    
    def test_get_files_sort_default_behavior(self, client: TestClient, sample_media_files):
        """测试默认排序行为（不指定sort参数）"""
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 默认应该是降序
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time >= next_time
    
    def test_get_files_invalid_sort_parameter(self, client: TestClient, sample_media_files):
        """测试无效的排序参数"""
        response = client.get("/api/files?sort=invalid_sort")
        assert response.status_code == 422
    
    def test_get_files_sort_original_filename_asc(self, client: TestClient, sample_media_files):
        """测试按文件名升序排序"""
        response = client.get("/api/files?sort=original_filename:asc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证文件名是按字母升序排列的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_name = items[i]["original_filename"].lower()
                next_name = items[i + 1]["original_filename"].lower()
                assert current_name <= next_name
    
    def test_get_files_sort_original_filename_desc(self, client: TestClient, sample_media_files):
        """测试按文件名降序排序"""
        response = client.get("/api/files?sort=original_filename:desc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证文件名是按字母降序排列的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_name = items[i]["original_filename"].lower()
                next_name = items[i + 1]["original_filename"].lower()
                assert current_name >= next_name
    
    def test_get_files_sort_status_asc(self, client: TestClient, sample_media_files):
        """测试按状态升序排序"""
        response = client.get("/api/files?sort=status:asc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证状态是按字母升序排列的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_status = items[i]["status"]
                next_status = items[i + 1]["status"]
                assert current_status <= next_status
    
    def test_get_files_sort_status_desc(self, client: TestClient, sample_media_files):
        """测试按状态降序排序"""
        response = client.get("/api/files?sort=status:desc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证状态是按字母降序排列的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_status = items[i]["status"]
                next_status = items[i + 1]["status"]
                assert current_status >= next_status
    
    def test_get_files_sort_updated_at_asc(self, client: TestClient, sample_media_files):
        """测试按更新时间升序排序"""
        response = client.get("/api/files?sort=updated_at:asc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证更新时间是升序的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["updated_at"]
                next_time = items[i + 1]["updated_at"]
                assert current_time <= next_time
    
    def test_get_files_sort_updated_at_desc(self, client: TestClient, sample_media_files):
        """测试按更新时间降序排序"""
        response = client.get("/api/files?sort=updated_at:desc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        
        # 验证更新时间是降序的
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["updated_at"]
                next_time = items[i + 1]["updated_at"]
                assert current_time >= next_time
    
    def test_get_files_sort_invalid_field(self, client: TestClient, sample_media_files):
        """测试无效的排序字段"""
        response = client.get("/api/files?sort=invalid_field:asc")
        assert response.status_code == 422
        
        data = response.json()
        assert "不支持的排序字段" in data["detail"]
        assert "invalid_field" in data["detail"]
        assert "created_at, updated_at, original_filename, status" in data["detail"]
    
    def test_get_files_sort_invalid_direction(self, client: TestClient, sample_media_files):
        """测试无效的排序方向"""
        response = client.get("/api/files?sort=created_at:invalid")
        assert response.status_code == 422
        
        data = response.json()
        assert "不支持的排序方向" in data["detail"]
        assert "invalid" in data["detail"]
        assert "asc, desc" in data["detail"]
    
    def test_get_files_sort_malformed_parameter(self, client: TestClient, sample_media_files):
        """测试格式错误的排序参数"""
        # 测试缺少冒号分隔符
        response = client.get("/api/files?sort=created_at_asc")
        assert response.status_code == 422
        
        data = response.json()
        assert "排序参数格式错误" in data["detail"]
        assert "field:direction" in data["detail"]
    
    def test_get_files_sort_empty_parameter(self, client: TestClient, sample_media_files):
        """测试空的排序参数"""
        response = client.get("/api/files?sort=")
        assert response.status_code == 200
        
        # 空参数应该使用默认排序（created_at:desc）
        data = response.json()
        items = data["items"]
        
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time >= next_time

    def test_get_files_search_and_status_filter(self, client: TestClient, sample_media_files):
        """测试搜索和状态筛选组合"""
        response = client.get(f"/api/files?search=movie&status={FileStatus.PENDING}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1  # 只有movie1.mp4是PENDING状态
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.PENDING
        assert "movie" in data["items"][0]["original_filename"].lower()
    
    def test_get_files_search_status_and_sort(self, client: TestClient, sample_media_files):
        """测试搜索、状态筛选和排序的组合"""
        response = client.get(f"/api/files?search=movie&status={FileStatus.COMPLETED}&sort=created_at:asc")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 1  # 只有movie2.mkv是COMPLETED状态
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == FileStatus.COMPLETED
        assert "movie" in data["items"][0]["original_filename"].lower()
    
    def test_get_files_all_parameters_combined(self, client: TestClient, sample_media_files):
        """测试所有参数组合使用"""
        response = client.get("/api/files?search=movie&sort=created_at:asc&skip=0&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2  # movie1.mp4 和 movie2.mkv
        assert data["skip"] == 0
        assert data["limit"] == 10
        assert len(data["items"]) == 2
        
        # 验证排序
        items = data["items"]
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_time = items[i]["created_at"]
                next_time = items[i + 1]["created_at"]
                assert current_time <= next_time

    def test_get_files_has_next_true(self, client: TestClient, sample_media_files):
        """测试 has_next 为 true 的情况"""
        # 设置 skip=0, limit=3，应该有 has_next=true（因为总共有6个文件）
        response = client.get("/api/files?skip=0&limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 3
        assert data["has_next"]
        assert not data["has_previous"]
        assert data["total"] == 6  # sample_media_files 包含6个文件

    def test_get_files_has_next_false(self, client: TestClient, sample_media_files):
        """测试 has_next 为 false 的情况"""
        # 设置 skip=3, limit=5，应该有 has_next=false（3+5>=6）
        response = client.get("/api/files?skip=3&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 3
        assert data["limit"] == 5
        assert not data["has_next"]
        assert data["has_previous"]

    def test_get_files_has_previous_true(self, client: TestClient, sample_media_files):
        """测试 has_previous 为 true 的情况"""
        # 设置 skip=2，应该有 has_previous=true
        response = client.get("/api/files?skip=2&limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 2
        assert data["limit"] == 2
        assert data["has_previous"]

    def test_get_files_has_previous_false(self, client: TestClient, sample_media_files):
        """测试 has_previous 为 false 的情况"""
        # 设置 skip=0，应该有 has_previous=false
        response = client.get("/api/files?skip=0&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 0
        assert not data["has_previous"]

    def test_get_files_pagination_boundary_conditions(self, client: TestClient, sample_media_files):
        """测试分页边界条件"""
        # 测试最后一页的完整情况
        response = client.get("/api/files?skip=5&limit=1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 5
        assert data["limit"] == 1
        assert not data["has_next"]  # 5+1 = 6 等于 total
        assert data["has_previous"]  # skip > 0
        assert len(data["items"]) == 1

    def test_get_files_pagination_beyond_total(self, client: TestClient, sample_media_files):
        """测试超出总数的分页情况"""
        # skip 超出总数
        response = client.get("/api/files?skip=10&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 5
        assert not data["has_next"]  # 10+5 > 6
        assert data["has_previous"]  # skip > 0
        assert len(data["items"]) == 0


class TestMediaFileDetailAPI:
    """测试媒体文件详情API端点"""
    
    def test_get_media_file_success(self, client: TestClient, sample_media_files):
        """测试成功获取存在的媒体文件详情"""
        # 使用第一个测试文件
        test_file = sample_media_files[0]
        
        response = client.get(f"/api/files/{test_file.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_file.id
        assert data["original_filename"] == test_file.original_filename
        assert data["original_filepath"] == test_file.original_filepath
        assert data["file_size"] == test_file.file_size
        assert data["status"] == test_file.status
        assert data["inode"] == test_file.inode
        assert data["device_id"] == test_file.device_id
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_media_file_not_found(self, client: TestClient, sample_media_files):
        """测试获取不存在的媒体文件，应返回404"""
        response = client.get("/api/files/99999")
        assert response.status_code == 404
        
        data = response.json()
        assert "媒体文件不存在" in data["detail"]
        assert "ID=99999" in data["detail"]
    
    def test_get_media_file_invalid_id_type(self, client: TestClient, sample_media_files):
        """测试使用无效的文件ID类型（非整数）"""
        response = client.get("/api/files/invalid_id")
        assert response.status_code == 422
    
    def test_get_media_file_negative_id(self, client: TestClient, sample_media_files):
        """测试使用负数作为文件ID"""
        response = client.get("/api/files/-1")
        assert response.status_code == 404
        
        data = response.json()
        assert "媒体文件不存在" in data["detail"]
        assert "ID=-1" in data["detail"]
    
    def test_get_media_file_zero_id(self, client: TestClient, sample_media_files):
        """测试使用0作为文件ID"""
        response = client.get("/api/files/0")
        assert response.status_code == 404
        
        data = response.json()
        assert "媒体文件不存在" in data["detail"]
        assert "ID=0" in data["detail"]
    
    def test_get_media_file_different_statuses(self, client: TestClient, sample_media_files):
        """测试获取不同状态的媒体文件详情"""
        # 测试每种状态的文件
        status_files = {
            FileStatus.PENDING: next(f for f in sample_media_files if f.status == FileStatus.PENDING),
            FileStatus.COMPLETED: next(f for f in sample_media_files if f.status == FileStatus.COMPLETED),
            FileStatus.FAILED: next(f for f in sample_media_files if f.status == FileStatus.FAILED),
            FileStatus.NO_MATCH: next(f for f in sample_media_files if f.status == FileStatus.NO_MATCH),
            FileStatus.PROCESSING: next(f for f in sample_media_files if f.status == FileStatus.PROCESSING),
            FileStatus.QUEUED: next(f for f in sample_media_files if f.status == FileStatus.QUEUED),
        }
        
        for status, file_obj in status_files.items():
            response = client.get(f"/api/files/{file_obj.id}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == file_obj.id
            assert data["status"] == status


class TestSuggestAPI:
    """测试文件名建议API端点"""
    
    def test_suggest_filenames_success(self, client: TestClient, sample_media_files):
        """测试成功获取文件名建议"""
        response = client.get("/api/files/suggest?keyword=movie")
        assert response.status_code == 200
        
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) == 2  # movie1.mp4 和 movie2.mkv
        
        # 验证建议都以关键字开头
        for suggestion in data["suggestions"]:
            assert suggestion.lower().startswith("movie")
    
    def test_suggest_filenames_case_insensitive(self, client: TestClient, sample_media_files):
        """测试大小写不敏感的建议"""
        response = client.get("/api/files/suggest?keyword=MOVIE")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["suggestions"]) == 2
        
        # 验证建议都包含movie（不区分大小写）
        for suggestion in data["suggestions"]:
            assert "movie" in suggestion.lower()
    
    def test_suggest_filenames_single_character(self, client: TestClient, sample_media_files):
        """测试单字符前缀建议"""
        response = client.get("/api/files/suggest?keyword=m")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["suggestions"]) == 2  # movie1.mp4 和 movie2.mkv
    
    def test_suggest_filenames_no_matches(self, client: TestClient, sample_media_files):
        """测试无匹配结果"""
        response = client.get("/api/files/suggest?keyword=nonexistent")
        assert response.status_code == 200
        
        data = response.json()
        assert data["suggestions"] == []
    
    def test_suggest_filenames_empty_keyword(self, client: TestClient, sample_media_files):
        """测试空关键字"""
        response = client.get("/api/files/suggest?keyword=")
        assert response.status_code == 200
        
        data = response.json()
        assert data["suggestions"] == []
    
    def test_suggest_filenames_whitespace_keyword(self, client: TestClient, sample_media_files):
        """测试只包含空格的关键字"""
        response = client.get("/api/files/suggest?keyword=   ")
        assert response.status_code == 200
        
        data = response.json()
        assert data["suggestions"] == []
    
    def test_suggest_filenames_with_limit(self, client: TestClient, sample_media_files):
        """测试限制返回数量"""
        response = client.get("/api/files/suggest?keyword=movie&limit=1")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["suggestions"]) == 1
    
    def test_suggest_filenames_limit_zero(self, client: TestClient, sample_media_files):
        """测试limit为0（应该返回422错误）"""
        response = client.get("/api/files/suggest?keyword=movie&limit=0")
        assert response.status_code == 422
    
    def test_suggest_filenames_limit_too_large(self, client: TestClient, sample_media_files):
        """测试limit超过最大值（应该返回422错误）"""
        response = client.get("/api/files/suggest?keyword=movie&limit=101")
        assert response.status_code == 422
    
    def test_suggest_filenames_missing_keyword(self, client: TestClient, sample_media_files):
        """测试缺少keyword参数（应该返回422错误）"""
        response = client.get("/api/files/suggest")
        assert response.status_code == 422
    
    def test_suggest_filenames_distinct_results(self, client: TestClient, session: Session):
        """测试结果去重功能"""
        # 添加重复的文件名
        duplicate_files = [
            MediaFile(
                inode=2001,
                device_id=3001,
                original_filepath="/test1/duplicate.mp4",
                original_filename="duplicate.mp4",
                file_size=1000000,
                status=FileStatus.PENDING
            ),
            MediaFile(
                inode=2002,
                device_id=3001,
                original_filepath="/test2/duplicate.mp4",
                original_filename="duplicate.mp4",
                file_size=1000000,
                status=FileStatus.COMPLETED
            ),
        ]
        
        for media_file in duplicate_files:
            session.add(media_file)
        session.commit()
        
        response = client.get("/api/files/suggest?keyword=duplicate")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["suggestions"]) == 1  # 应该去重，只返回一个
        assert data["suggestions"][0] == "duplicate.mp4"
    
    def test_suggest_filenames_empty_database(self, client: TestClient):
        """测试空数据库"""
        response = client.get("/api/files/suggest?keyword=any")
        assert response.status_code == 200
        
        data = response.json()
        assert data["suggestions"] == []


class TestRetryAPI:
    """测试重试API端点"""
    
    def test_retry_failed_file_success(self, client: TestClient, sample_media_files, mock_queue, session: Session):
        """测试成功重试失败状态的文件"""
        # 找到FAILED状态的文件
        failed_file = next(f for f in sample_media_files if f.status == FileStatus.FAILED)
        
        response = client.post(f"/api/files/{failed_file.id}/retry")
        assert response.status_code == 200
        
        data = response.json()
        assert "文件状态已成功重置" in data["message"]
        assert data["file_id"] == failed_file.id
        assert data["previous_status"] == FileStatus.FAILED
        assert data["current_status"] == FileStatus.PENDING
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
        
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
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
        
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

    def test_retry_queued_file_not_allowed(self, client: TestClient, sample_media_files, mock_queue):
        """测试重试QUEUED状态的文件（不允许）"""
        # 找到QUEUED状态的文件
        queued_file = next(f for f in sample_media_files if f.status == FileStatus.QUEUED)
        
        response = client.post(f"/api/files/{queued_file.id}/retry")
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
        
        # 验证返回的统计数据，现在包含QUEUED状态
        expected_stats = {
            FileStatus.PENDING: 1,
            FileStatus.COMPLETED: 1,
            FileStatus.FAILED: 1,
            FileStatus.NO_MATCH: 1,
            FileStatus.PROCESSING: 1,
            FileStatus.QUEUED: 1
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

@pytest.fixture(name="basic_media_files")
def basic_media_files_fixture(session: Session):
    """提供包含CONFLICT状态在内的媒体文件集合，用于补充测试。"""
    from app.core.models import MediaFile, FileStatus  # 局部导入避免循环

    media_files = [
        MediaFile(
            inode=2001,
            device_id=3001,
            original_filepath="/test/retry_failed.mp4",
            original_filename="retry_failed.mp4",
            file_size=1000000,
            status=FileStatus.FAILED,
        ),
        MediaFile(
            inode=2002,
            device_id=3001,
            original_filepath="/test/retry_no_match.mp4",
            original_filename="retry_no_match.mp4",
            file_size=2000000,
            status=FileStatus.NO_MATCH,
        ),
        MediaFile(
            inode=2003,
            device_id=3001,
            original_filepath="/test/retry_conflict.mp4",
            original_filename="retry_conflict.mp4",
            file_size=1500000,
            status=FileStatus.CONFLICT,
        ),
    ]
    for mf in media_files:
        session.add(mf)
    session.commit()
    for mf in media_files:
        session.refresh(mf)
    return media_files


class TestRetryAPIAdditional:
    """补充Retry API的异常及CONFLICT场景测试。"""

    def test_retry_conflict_status_file(self, client: TestClient, basic_media_files, mock_queue, session: Session):
        """CONFLICT 状态文件可成功重试。"""
        from app.core.models import FileStatus

        conflict_file = next(f for f in basic_media_files if f.status == FileStatus.CONFLICT)
        resp = client.post(f"/api/files/{conflict_file.id}/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["previous_status"] == FileStatus.CONFLICT
        assert data["current_status"] == FileStatus.PENDING
        
        # 验证队列未被调用
        mock_queue.put.assert_not_called()
        
        # 验证数据库状态
        session.refresh(conflict_file)
        assert conflict_file.status == FileStatus.PENDING


class TestFilesAPIEdgeCases:
    """补充文件列表 API 的极端和特殊字符场景。"""

    def test_files_with_extremely_large_skip(self, client: TestClient, sample_media_files):
        resp = client.get("/api/files?skip=1000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skip"] == 1000000
        assert len(data["items"]) == 0

    def test_files_search_with_special_characters(self, client: TestClient, session: Session):
        from app.core.models import MediaFile, FileStatus

        special = MediaFile(
            inode=3001,
            device_id=4001,
            original_filepath="/test/file-with-special@#$.mp4",
            original_filename="file-with-special@#$.mp4",
            file_size=1000000,
            status=FileStatus.PENDING,
        )
        session.add(special)
        session.commit()
        session.refresh(special)

        resp = client.get("/api/files?search=@#$")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "@#$" in data["items"][0]["original_filename"]


class TestSuggestAPIEdgeCases:
    """建议 API 的安全与极端边界测试。"""

    def test_suggest_with_sql_injection_attempt(self, client: TestClient, sample_media_files):
        malicious = "'; DROP TABLE mediafile; --"
        resp = client.get(f"/api/files/suggest?keyword={malicious}")
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []

    def test_suggest_with_unicode_characters(self, client: TestClient, session: Session):
        from app.core.models import MediaFile, FileStatus

        uni_file = MediaFile(
            inode=4001,
            device_id=5001,
            original_filepath="/test/电影名称.mp4",
            original_filename="电影名称.mp4",
            file_size=1000000,
            status=FileStatus.PENDING,
        )
        session.add(uni_file)
        session.commit()

        resp = client.get("/api/files/suggest?keyword=电影")
        assert resp.status_code == 200
        assert "电影名称.mp4" in resp.json()["suggestions"]

    def test_suggest_with_very_long_keyword(self, client: TestClient):
        long_kw = "a" * 1000
        resp = client.get(f"/api/files/suggest?keyword={long_kw}")
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []


class TestStatsAPIEdgeCases:
    """统计 API 的额外边界测试。"""

    def test_stats_with_only_one_status_type(self, client: TestClient, session: Session):
        from sqlmodel import delete
        from app.core.models import MediaFile, FileStatus

        session.exec(delete(MediaFile))
        for i in range(3):
            session.add(
                MediaFile(
                    inode=5000 + i,
                    device_id=6001,
                    original_filepath=f"/test/pending_{i}.mp4",
                    original_filename=f"pending_{i}.mp4",
                    file_size=1000000,
                    status=FileStatus.PENDING,
                )
            )
        session.commit()
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {FileStatus.PENDING: 3}

    def test_stats_with_mixed_status_distribution(self, client: TestClient, session: Session):
        from sqlmodel import delete
        from app.core.models import MediaFile, FileStatus

        session.exec(delete(MediaFile))
        status_counts = {
            FileStatus.PENDING: 3,
            FileStatus.QUEUED: 1,
            FileStatus.PROCESSING: 1,
            FileStatus.COMPLETED: 5,
            FileStatus.FAILED: 2,
            FileStatus.CONFLICT: 1,
            FileStatus.NO_MATCH: 2,
        }
        fid = 7000
        for status, cnt in status_counts.items():
            for _ in range(cnt):
                session.add(
                    MediaFile(
                        inode=fid,
                        device_id=8001,
                        original_filepath=f"/test/{status}_{fid}.mp4",
                        original_filename=f"{status}_{fid}.mp4",
                        file_size=1000000,
                        status=status,
                    )
                )
                fid += 1
        session.commit()
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert all(data[st] == c for st, c in status_counts.items())


class TestMediaFileDetailEdgeCases:
    """媒体文件详情 API 的额外边界测试。"""

    def test_get_file_with_max_integer_id(self, client: TestClient):
        max_id = 2_147_483_647
        resp = client.get(f"/api/files/{max_id}")
        assert resp.status_code == 404

    def test_get_file_with_float_id_in_url(self, client: TestClient):
        resp = client.get("/api/files/123.456")
        assert resp.status_code == 422


class TestAPIResponseStructure:
    """验证API响应结构完整性。"""

    def test_files_response_structure(self, client: TestClient, sample_media_files):
        resp = client.get("/api/files")
        data = resp.json()
        assert set(data.keys()) == {"total", "skip", "limit", "has_next", "has_previous", "items"}
        if data["items"]:
            first = data["items"][0]
            required = {"id", "inode", "device_id", "original_filepath", "original_filename", "file_size", "status", "created_at", "updated_at"}
            assert required.issubset(first.keys())

    def test_retry_response_structure(self, client: TestClient, basic_media_files, mock_queue):
        from app.core.models import FileStatus
        fail_file = next(f for f in basic_media_files if f.status == FileStatus.FAILED)
        resp = client.post(f"/api/files/{fail_file.id}/retry")
        data = resp.json()
        assert set(data.keys()) == {"message", "file_id", "previous_status", "current_status"} 