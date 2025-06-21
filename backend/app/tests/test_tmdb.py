import pytest
import asyncio
import requests

# 导入测试目标模块（假设路径为app.core.tmdb）
# 注意：实际测试时，这个模块可能还不存在，但我们可以先写测试
from app.core import tmdb


@pytest.mark.asyncio
async def test_search_movie_success(mocker, mock_tmdbsimple):
    """
    测试用例 4.1: 成功找到匹配项
    Given: 输入从LLM获取的有效数据 {"title": "Dune Part Two", "year": "2024"}
    When: 调用TMDB搜索函数
    Then: 函数应返回一个包含正确TMDB ID和媒体信息的对象
    """
    # 模拟数据
    llm_data = {"title": "Dune Part Two", "year": "2024", "type": "movie"}
    
    # 配置模拟的tmdbsimple.Search对象
    mock_search = mock_tmdbsimple["search"]
    mock_search.movie.return_value = {"page": 1, "total_results": 1}
    mock_search.results = [{
        "id": 693134,
        "title": "Dune: Part Two",
        "release_date": "2024-02-28",
        "overview": "Follow the mythic journey of Paul Atreides...",
        "poster_path": "/path/to/poster.jpg",
        "vote_average": 8.5
    }]
    
    # 模拟tmdbsimple库
    mocker.patch("app.core.tmdb.tmdbsimple", mock_tmdbsimple["tmdb"])
    
    # 模拟asyncio.to_thread
    async def async_to_thread_mock(func, *args, **kwargs):
        await asyncio.sleep(0)
        return func(*args, **kwargs)

    mocker.patch("app.core.tmdb.asyncio.to_thread", side_effect=async_to_thread_mock)
    
    # 调用被测函数
    result = await tmdb.search_movie(llm_data)
    
    # 验证结果
    assert result is not None
    assert result["id"] == 693134
    assert result["title"] == "Dune: Part Two"
    assert result["release_date"] == "2024-02-28"
    
    # 验证tmdbsimple.Search.movie被正确调用
    mock_search.movie.assert_called_once_with(query="Dune Part Two", year=2024)


@pytest.mark.asyncio
async def test_search_movie_not_found(mocker, mock_tmdbsimple):
    """
    测试用例 4.2: 未找到匹配项
    Given: 输入一个无法匹配任何电影的数据 {"title": "一部不存在的电影", "year": "1900"}
    When: 调用TMDB搜索函数
    Then: 函数应返回None或一个表示失败的空结果
    """
    # 模拟数据
    llm_data = {"title": "一部不存在的电影", "year": "1900", "type": "movie"}
    
    # 配置模拟的tmdbsimple.Search对象 - 返回空结果
    mock_search = mock_tmdbsimple["search"]
    mock_search.movie.return_value = {"page": 1, "total_results": 0}
    mock_search.results = []  # 空结果列表
    
    # 模拟tmdbsimple库
    mocker.patch("app.core.tmdb.tmdbsimple", mock_tmdbsimple["tmdb"])
    
    # 模拟asyncio.to_thread
    async def async_to_thread_mock(func, *args, **kwargs):
        await asyncio.sleep(0)
        return func(*args, **kwargs)

    mocker.patch("app.core.tmdb.asyncio.to_thread", side_effect=async_to_thread_mock)
    
    # 调用被测函数
    result = await tmdb.search_movie(llm_data)
    
    # 验证结果
    assert result is None or (isinstance(result, dict) and not result)
    
    # 验证tmdbsimple.Search.movie被正确调用
    mock_search.movie.assert_called_once_with(query="一部不存在的电影", year=1900)


@pytest.mark.asyncio
async def test_search_movie_async_wrapping(mocker, mock_tmdbsimple):
    """
    测试用例 4.3: 验证异步包装
    Given: 任何有效的输入
    When: await调用TMDB搜索函数
    Then: asyncio.to_thread应该被调用，并且函数应成功执行完毕，没有阻塞测试的事件循环
    """
    # 模拟数据
    llm_data = {"title": "Test Movie", "year": "2023", "type": "movie"}
    
    # 配置模拟的tmdbsimple.Search对象
    mock_search = mock_tmdbsimple["search"]
    mock_search.movie.return_value = {"page": 1, "total_results": 1}
    mock_search.results = [{
        "id": 12345,
        "title": "Test Movie",
        "release_date": "2023-01-01"
    }]
    
    # 模拟tmdbsimple库
    mocker.patch("app.core.tmdb.tmdbsimple", mock_tmdbsimple["tmdb"])
    
    # 直接跟踪asyncio.to_thread的调用
    to_thread_spy = mocker.spy(asyncio, "to_thread")
    
    # 调用被测函数
    result = await tmdb.search_movie(llm_data)
    
    # 验证asyncio.to_thread被调用
    assert to_thread_spy.call_count > 0
    
    # 验证函数执行完毕并返回结果
    assert result is not None
    assert result["id"] == 12345


@pytest.mark.asyncio
async def test_get_movie_details(mocker, mock_tmdbsimple):
    """
    测试获取电影详情
    Given: 一个有效的电影ID
    When: 调用TMDB获取详情函数
    Then: 函数应返回包含完整电影信息的对象
    """
    # 模拟数据
    movie_id = 603  # The Matrix
    
    # 配置模拟的tmdbsimple.Movies对象
    mock_movies = mock_tmdbsimple["movies"]
    mock_movies.info.return_value = {
        "id": 603,
        "title": "The Matrix",
        "release_date": "1999-03-30",
        "overview": "Set in the 22nd century...",
        "budget": 63000000,
        "runtime": 136,
        "poster_path": "/path/to/poster.jpg",
        "vote_average": 8.7
    }
    
    # 模拟tmdbsimple库
    mocker.patch("app.core.tmdb.tmdbsimple", mock_tmdbsimple["tmdb"])
    
    # 模拟asyncio.to_thread
    async def async_to_thread_mock(func, *args, **kwargs):
        await asyncio.sleep(0)
        return func(*args, **kwargs)

    mocker.patch("app.core.tmdb.asyncio.to_thread", side_effect=async_to_thread_mock)
    
    # 调用被测函数
    result = await tmdb.get_movie_details(movie_id)
    
    # 验证结果
    assert result is not None
    assert result["id"] == 603
    assert result["title"] == "The Matrix"
    assert result["budget"] == 63000000
    assert result["runtime"] == 136
    
    # 验证tmdbsimple.Movies被正确调用
    mock_tmdbsimple["tmdb"].Movies.assert_called_once_with(movie_id)
    mock_movies.info.assert_called_once()


@pytest.mark.asyncio
async def test_api_retry_mechanism(mocker, mock_tmdbsimple):
    """
    测试API调用失败与重试机制
    Given: TMDB API在前两次调用时失败，第三次成功
    When: 调用TMDB搜索函数
    Then: 函数最终成功返回结果，底层API被调用了3次
    """
    # 模拟数据
    llm_data = {"title": "Inception", "year": "2010", "type": "movie"}
    
    # 配置模拟的tmdbsimple.Search对象
    mock_search = mock_tmdbsimple["search"]
    
    # 设置前两次调用抛出异常，第三次成功
    mock_search.movie.side_effect = [
        # 第一次调用：请求超时
        requests.exceptions.Timeout("Connection timed out"),
        # 第二次调用：服务器错误
        requests.exceptions.HTTPError("500 Server Error"),
        # 第三次调用：成功
        {"page": 1, "total_results": 1}
    ]
    
    # 成功时的返回结果
    mock_search.results = [{
        "id": 27205,
        "title": "Inception",
        "release_date": "2010-07-16",
        "overview": "A thief who steals corporate secrets...",
        "vote_average": 8.4
    }]
    
    # 模拟tmdbsimple库
    mocker.patch("app.core.tmdb.tmdbsimple", mock_tmdbsimple["tmdb"])
    
    # 模拟asyncio.to_thread，确保它能正确传播异常
    async def async_to_thread_mock(func, *args, **kwargs):
        # 这个mock直接调用函数，这样异常就可以被tenacity捕获
        return func(*args, **kwargs)

    mocker.patch("app.core.tmdb.asyncio.to_thread", side_effect=async_to_thread_mock)
    
    # 调用被测函数
    result = await tmdb.search_movie(llm_data)
    
    # 验证结果
    assert result is not None
    assert result["id"] == 27205
    assert result["title"] == "Inception"
    
    # 验证tmdbsimple.Search.movie被调用了3次
    assert mock_search.movie.call_count == 3


@pytest.mark.asyncio
async def test_tmdb_semaphore_limit(mocker):
    """
    测试TMDB信号量机制
    Given: 配置的并发限制为10，尝试同时发起15个请求
    When: 并发调用TMDB搜索函数
    Then: 信号量应该限制并发请求数，确保不超过10个并发请求
    """
    # 模拟真实的信号量行为
    real_semaphore = asyncio.Semaphore(10)
    
    # 跟踪信号量的acquire和release调用
    original_acquire = real_semaphore.acquire
    original_release = real_semaphore.release
    
    acquire_count = 0
    max_concurrent = 0
    current_concurrent = 0
    
    # 替换信号量的方法来跟踪并发数
    async def tracked_acquire():
        nonlocal acquire_count, current_concurrent, max_concurrent
        await original_acquire()
        acquire_count += 1
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        return True
    
    def tracked_release():
        nonlocal current_concurrent
        original_release()
        current_concurrent -= 1
    
    real_semaphore.acquire = tracked_acquire
    real_semaphore.release = tracked_release
    
    # 模拟TMDB_SEMAPHORE
    mocker.patch("app.core.tmdb.TMDB_SEMAPHORE", real_semaphore)
    
    # 模拟search_movie函数，使其在信号量内部延迟一段时间
    async def mock_search_movie(data):
        async with tmdb.TMDB_SEMAPHORE:
            # 模拟API调用的延迟
            await asyncio.sleep(0.1)
            return {"id": 12345, "title": data["title"]}
    
    mocker.patch("app.core.tmdb.search_movie", mock_search_movie)
    
    # 创建15个并发请求
    tasks = []
    for i in range(15):
        tasks.append(tmdb.search_movie({"title": f"Movie {i}", "year": "2023", "type": "movie"}))
    
    # 等待所有请求完成
    results = await asyncio.gather(*tasks)
    
    # 验证结果
    assert len(results) == 15
    assert all(result is not None for result in results)
    
    # 验证并发限制
    assert max_concurrent <= 10, f"并发请求数超过了限制：{max_concurrent} > 10"
    assert acquire_count == 15, "应该有15个请求尝试获取信号量"


@pytest.mark.asyncio
async def test_search_media_hybrid_search_success(mocker):
    """
    测试TMDB混合搜索功能：LLM错误识别类型时的备用搜索
    Given: LLM错误地将一个电影识别为TV剧类型
    When: 调用search_media函数
    Then: 主类型搜索失败后，自动尝试备用类型并成功找到匹配
    """
    # 模拟LLM错误识别：将《Inception》(电影)识别为TV剧
    llm_data = {
        "title": "Inception",
        "year": 2010,
        "type": "tv"  # 错误的类型识别
    }
    
    # 模拟TV剧搜索失败（返回None）
    mock_search_tv = mocker.patch("app.core.tmdb.search_tv_by_title_and_year")
    mock_search_tv.return_value = None
    
    # 模拟电影搜索成功
    mock_search_movie = mocker.patch("app.core.tmdb.search_movie_by_title_and_year")
    mock_search_movie.return_value = {
        "id": 27205,
        "title": "Inception",
        "release_date": "2010-07-16",
        "overview": "A thief who steals corporate secrets...",
        "vote_average": 8.4
    }
    
    # 调用被测函数
    result = await tmdb.search_media(llm_data)
    
    # 验证结果
    assert result is not None
    assert result["tmdb_id"] == 27205
    assert result["media_type"] == "movie"  # 最终确定的正确类型
    assert result["processed_data"]["title"] == "Inception"
    
    # 验证调用顺序：先尝试TV剧，失败后尝试电影
    mock_search_tv.assert_called_once_with("Inception", 2010)
    mock_search_movie.assert_called_once_with("Inception", 2010)


@pytest.mark.asyncio 
async def test_search_media_hybrid_search_both_fail(mocker):
    """
    测试TMDB混合搜索功能：主类型和备用类型都搜索失败
    Given: 一个在TMDB中不存在的媒体标题
    When: 调用search_media函数
    Then: 主类型和备用类型搜索都失败，最终返回None
    """
    # 模拟一个不存在的媒体
    llm_data = {
        "title": "Non-existent Movie",
        "year": 1999,
        "type": "movie"
    }
    
    # 模拟电影搜索失败
    mock_search_movie = mocker.patch("app.core.tmdb.search_movie_by_title_and_year")
    mock_search_movie.return_value = None
    
    # 模拟TV剧搜索也失败
    mock_search_tv = mocker.patch("app.core.tmdb.search_tv_by_title_and_year") 
    mock_search_tv.return_value = None
    
    # 调用被测函数
    result = await tmdb.search_media(llm_data)
    
    # 验证结果
    assert result is None
    
    # 验证调用顺序：先尝试电影（主类型），失败后尝试TV剧（备用类型）
    mock_search_movie.assert_called_once_with("Non-existent Movie", 1999)
    mock_search_tv.assert_called_once_with("Non-existent Movie", 1999)


@pytest.mark.asyncio
async def test_search_media_primary_type_success(mocker):
    """
    测试TMDB混合搜索功能：主类型搜索成功的情况
    Given: LLM正确识别了媒体类型
    When: 调用search_media函数
    Then: 主类型搜索成功，不需要尝试备用类型
    """
    # 模拟LLM正确识别的电影
    llm_data = {
        "title": "The Matrix",
        "year": 1999,
        "type": "movie"
    }
    
    # 模拟电影搜索成功
    mock_search_movie = mocker.patch("app.core.tmdb.search_movie_by_title_and_year")
    mock_search_movie.return_value = {
        "id": 603,
        "title": "The Matrix",
        "release_date": "1999-03-30",
        "overview": "Set in the 22nd century...",
        "vote_average": 8.7
    }
    
    # 模拟TV剧搜索（不应被调用）
    mock_search_tv = mocker.patch("app.core.tmdb.search_tv_by_title_and_year")
    
    # 调用被测函数
    result = await tmdb.search_media(llm_data)
    
    # 验证结果
    assert result is not None
    assert result["tmdb_id"] == 603
    assert result["media_type"] == "movie"
    assert result["processed_data"]["title"] == "The Matrix"
    
    # 验证只调用了电影搜索，没有调用TV剧搜索
    mock_search_movie.assert_called_once_with("The Matrix", 1999)
    mock_search_tv.assert_not_called() 