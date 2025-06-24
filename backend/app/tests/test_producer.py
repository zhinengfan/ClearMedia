"""
producer.py 单元测试

测试 Producer 组件的各种场景：批量处理、队列操作、状态转换等
"""

import pytest
import asyncio
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.pool import StaticPool

from app.core.models import MediaFile, FileStatus
from app.services.media.producer import producer_single_run, _process_batch


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
def sample_pending_files(db_session_factory):
    """创建多个 PENDING 状态的测试文件"""
    with db_session_factory() as session:
        files = []
        for i in range(5):
            media_file = MediaFile(
                inode=100000 + i,
                device_id=200000,
                original_filepath=f"/test/movie{i+1}.mp4",
                original_filename=f"movie{i+1}.mp4",
                file_size=1024 * 1024 * (10 + i),  # 不同大小
                status=FileStatus.PENDING
            )
            session.add(media_file)
            files.append(media_file)
        
        session.commit()
        
        # 刷新以获取数据库分配的ID
        for file in files:
            session.refresh(file)
        
        return files


@pytest.fixture
def mixed_status_files(db_session_factory):
    """创建混合状态的测试文件"""
    with db_session_factory() as session:
        files = []
        statuses = [FileStatus.PENDING, FileStatus.QUEUED, FileStatus.PROCESSING, FileStatus.COMPLETED, FileStatus.FAILED]
        
        for i, status in enumerate(statuses):
            media_file = MediaFile(
                inode=300000 + i,
                device_id=400000,
                original_filepath=f"/test/mixed{i+1}.mp4",
                original_filename=f"mixed{i+1}.mp4",
                file_size=1024 * 1024 * 10,
                status=status
            )
            session.add(media_file)
            files.append(media_file)
        
        session.commit()
        
        for file in files:
            session.refresh(file)
        
        return files


class TestProducerSingleRun:
    """测试 Producer 单次运行功能"""
    
    @pytest.mark.asyncio
    async def test_producer_single_run_basic(self, db_session_factory, sample_pending_files):
        """测试基础的单次运行功能"""
        # 创建队列
        queue = asyncio.Queue()
        
        # 运行 Producer
        processed_count = await producer_single_run(db_session_factory, queue, batch_size=3)
        
        # 验证处理数量
        assert processed_count == 3  # 应该只处理 batch_size 数量的文件
        
        # 验证队列大小
        assert queue.qsize() == 3
        
        # 验证数据库状态变化
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            queued_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.QUEUED)).all()
            
            assert len(pending_files) == 2  # 剩余 2 个 PENDING
            assert len(queued_files) == 3   # 3 个变成 QUEUED
        
        # 验证队列中的文件ID
        queued_ids = []
        while not queue.empty():
            file_id = await queue.get()
            queued_ids.append(file_id)
        
        assert len(queued_ids) == 3
        
        # 验证这些ID对应的文件确实是 QUEUED 状态
        with db_session_factory() as session:
            for file_id in queued_ids:
                file = session.get(MediaFile, file_id)
                assert file is not None
                assert file.status == FileStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_producer_single_run_large_batch(self, db_session_factory, sample_pending_files):
        """测试批量大小大于可用文件数的情况"""
        queue = asyncio.Queue()
        
        # 批量大小大于文件数
        processed_count = await producer_single_run(db_session_factory, queue, batch_size=10)
        
        # 应该处理所有 5 个文件
        assert processed_count == 5
        assert queue.qsize() == 5
        
        # 验证所有文件都变成 QUEUED
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            queued_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.QUEUED)).all()
            
            assert len(pending_files) == 0
            assert len(queued_files) == 5
    
    @pytest.mark.asyncio
    async def test_producer_single_run_no_pending_files(self, db_session_factory):
        """测试没有 PENDING 文件的情况"""
        queue = asyncio.Queue()
        
        # 没有文件的情况下运行
        processed_count = await producer_single_run(db_session_factory, queue, batch_size=5)
        
        assert processed_count == 0
        assert queue.qsize() == 0
    
    @pytest.mark.asyncio
    async def test_producer_single_run_mixed_status(self, db_session_factory, mixed_status_files):
        """测试混合状态文件，只处理 PENDING 状态的文件"""
        queue = asyncio.Queue()
        
        processed_count = await producer_single_run(db_session_factory, queue, batch_size=10)
        
        # 只有 1 个 PENDING 文件应该被处理
        assert processed_count == 1
        assert queue.qsize() == 1
        
        # 验证状态分布
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            queued_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.QUEUED)).all()
            
            assert len(pending_files) == 0  # 原来的 PENDING 文件被处理了
            assert len(queued_files) == 2   # 原来的 1 个 QUEUED + 新处理的 1 个
    
    @pytest.mark.asyncio
    async def test_producer_single_run_multiple_calls(self, db_session_factory, sample_pending_files):
        """测试多次调用 Producer 的情况"""
        queue = asyncio.Queue()
        
        # 第一次调用
        processed_count_1 = await producer_single_run(db_session_factory, queue, batch_size=2)
        assert processed_count_1 == 2
        
        # 第二次调用
        processed_count_2 = await producer_single_run(db_session_factory, queue, batch_size=2)
        assert processed_count_2 == 2
        
        # 第三次调用
        processed_count_3 = await producer_single_run(db_session_factory, queue, batch_size=2)
        assert processed_count_3 == 1  # 只剩 1 个文件
        
        # 第四次调用
        processed_count_4 = await producer_single_run(db_session_factory, queue, batch_size=2)
        assert processed_count_4 == 0  # 没有文件了
        
        # 验证总体结果
        assert queue.qsize() == 5  # 总共 5 个文件都被处理了
        
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            queued_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.QUEUED)).all()
            
            assert len(pending_files) == 0
            assert len(queued_files) == 5


class TestProducerProcessBatch:
    """测试 Producer 内部批处理逻辑"""
    
    @pytest.mark.asyncio
    async def test_process_batch_basic(self, db_session_factory, sample_pending_files):
        """测试基础批处理功能"""
        queue = asyncio.Queue()
        
        processed_count = await _process_batch(db_session_factory, queue, batch_size=3)
        
        assert processed_count == 3
        assert queue.qsize() == 3
    
    @pytest.mark.asyncio
    async def test_process_batch_empty_database(self, db_session_factory):
        """测试空数据库的批处理"""
        queue = asyncio.Queue()
        
        processed_count = await _process_batch(db_session_factory, queue, batch_size=5)
        
        assert processed_count == 0
        assert queue.qsize() == 0


class TestProducerEdgeCases:
    """测试 Producer 的边界情况和异常处理"""
    
    @pytest.mark.asyncio
    async def test_producer_with_zero_batch_size(self, db_session_factory, sample_pending_files):
        """测试批量大小为 0 的情况（边界条件）"""
        queue = asyncio.Queue()
        
        # 批量大小为 0 应该不处理任何文件
        processed_count = await producer_single_run(db_session_factory, queue, batch_size=0)
        
        assert processed_count == 0
        assert queue.qsize() == 0
        
        # 验证所有文件仍然是 PENDING 状态
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            assert len(pending_files) == 5
    
    @pytest.mark.asyncio
    async def test_producer_sequential_access(self, db_session_factory, sample_pending_files):
        """测试顺序访问的情况（避免并发复杂性）"""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        
        # 顺序运行两个 Producer
        processed_count_1 = await producer_single_run(db_session_factory, queue1, batch_size=3)
        processed_count_2 = await producer_single_run(db_session_factory, queue2, batch_size=3)
        
        # 第一次应该处理 3 个，第二次应该处理 2 个
        assert processed_count_1 == 3
        assert processed_count_2 == 2
        
        # 验证队列大小
        assert queue1.qsize() == 3
        assert queue2.qsize() == 2
        
        # 验证没有文件被重复处理
        all_queued_ids = set()
        
        while not queue1.empty():
            file_id = await queue1.get()
            all_queued_ids.add(file_id)
            
        while not queue2.empty():
            file_id = await queue2.get()
            all_queued_ids.add(file_id)
        
        # 应该有 5 个不同的文件ID
        assert len(all_queued_ids) == 5
        
        # 验证所有文件都是 QUEUED 状态
        with db_session_factory() as session:
            pending_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.PENDING)).all()
            queued_files = session.exec(select(MediaFile).where(MediaFile.status == FileStatus.QUEUED)).all()
            
            assert len(pending_files) == 0  # 没有 PENDING 文件
            assert len(queued_files) == 5   # 5 个文件都变成 QUEUED 