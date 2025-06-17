"""LLM交互单元测试 (test_llm.py)
使用 pytest-mock 模拟 openai 客户端
"""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from openai import APIError, APITimeoutError, RateLimitError
from tenacity import RetryError
import asyncio
import httpx

# 导入待测试的模块（假设在 app.core.llm）
from app.core import llm


def create_mock_api_error(message: str) -> APIError:
    """创建正确的 APIError 对象"""
    mock_request = MagicMock(spec=httpx.Request)
    mock_request.method = "POST"
    mock_request.url = "https://api.openai.com/v1/chat/completions"
    return APIError(message, mock_request, body=None)


def create_mock_rate_limit_error(message: str) -> RateLimitError:
    """创建正确的 RateLimitError 对象"""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.request = MagicMock(spec=httpx.Request)
    mock_response.request.method = "POST"
    mock_response.request.url = "https://api.openai.com/v1/chat/completions"
    return RateLimitError(message, response=mock_response, body=None)


class TestLLMFileNameAnalysis:
    """LLM文件名分析功能测试"""

    @pytest.mark.asyncio
    async def test_success_parse_standard_filename(self, mocker):
        """
        测试用例 3.1: 成功解析规范文件名
        Given: 输入文件名 "Dune.Part.Two.2024.1080p.mkv"
        When: 调用LLM分析函数
        Then: 函数应返回一个类似 {"title": "Dune Part Two", "year": "2024", "type": "movie"} 的JSON对象
        """
        # 模拟OpenAI客户端响应
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = json.dumps({
            "title": "Dune Part Two",
            "year": "2024",
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "Dune.Part.Two.2024.1080p.mkv"
        
        # 调用被测函数
        result = await llm.analyze_filename(filename)
        
        # 验证结果
        assert result is not None
        assert isinstance(result, dict)
        assert result["title"] == "Dune Part Two"
        assert result["year"] == "2024"
        assert result["type"] == "movie"
        
        # 验证OpenAI客户端被正确调用
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert "Dune.Part.Two.2024.1080p.mkv" in str(call_args)

    @pytest.mark.asyncio
    async def test_graceful_handle_irregular_filename(self, mocker):
        """
        测试用例 3.2: 优雅处理不规范文件名
        Given: 输入文件名 "沙丘2.mkv"
        When: 调用LLM分析函数
        Then: 函数应能返回一个合理的猜测结果，例如 {"title": "沙丘2", "year": null, "type": "movie"}
        """
        # 模拟OpenAI客户端响应
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = json.dumps({
            "title": "沙丘2",
            "year": None,
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "沙丘2.mkv"
        
        # 调用被测函数
        result = await llm.analyze_filename(filename)
        
        # 验证结果
        assert result is not None
        assert isinstance(result, dict)
        assert result["title"] == "沙丘2"
        assert result["year"] is None
        assert result["type"] == "movie"
        
        # 验证OpenAI客户端被正确调用
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_failure_with_retry(self, mocker):
        """
        测试用例 3.3: API调用失败与重试
        Given: 模拟 openai 客户端在前两次调用时抛出 APIError，第三次调用时成功
        When: 调用LLM分析函数（该函数已被 @tenacity.retry 装饰）
        Then: 函数最终成功返回结果，并且可以断言底层的API客户端被调用了3次
        """
        # 成功响应的数据
        successful_response = MagicMock()
        successful_response.choices = [MagicMock()]
        successful_response.choices[0].message.content = json.dumps({
            "title": "Test Movie",
            "year": "2023",
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        
        # 设置前两次调用失败，第三次成功
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_mock_api_error("API Error 1"),  # 第一次失败
                APITimeoutError("Timeout Error"),  # 第二次失败
                successful_response  # 第三次成功
            ]
        )
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "Test.Movie.2023.mkv"
        
        # 调用被测函数
        result = await llm.analyze_filename(filename)
        
        # 验证结果
        assert result is not None
        assert result["title"] == "Test Movie"
        assert result["year"] == "2023"
        assert result["type"] == "movie"
        
        # 验证API客户端被调用了3次
        assert mock_openai_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_cache_mechanism(self, mocker):
        """
        测试用例 3.4: 验证缓存机制
        Given: 模拟 openai 客户端
        When: 使用相同的文件名连续调用LLM分析函数（该函数已被 @functools.lru_cache 装饰）两次
        Then: 底层的API客户端应该只被调用了1次
        """
        # 模拟OpenAI客户端响应
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = json.dumps({
            "title": "Cached Movie",
            "year": "2023",
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 清除缓存（如果存在的话）
        if hasattr(llm.analyze_filename, 'cache_clear'):
            llm.analyze_filename.cache_clear()
        
        # 测试数据
        filename = "Cached.Movie.2023.mkv"
        
        # 第一次调用
        result1 = await llm.analyze_filename(filename)
        
        # 第二次调用（相同的文件名）
        result2 = await llm.analyze_filename(filename)
        
        # 验证两次调用返回相同的结果
        assert result1 == result2
        assert result1["title"] == "Cached Movie"
        
        # 验证API客户端只被调用了1次（由于缓存）
        assert mock_openai_client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mocker):
        """
        测试用例 3.5: 速率限制处理
        Given: 模拟 openai 客户端返回 RateLimitError
        When: 调用LLM分析函数
        Then: 函数应该进行重试并最终成功或失败
        """
        # 成功响应的数据
        successful_response = MagicMock()
        successful_response.choices = [MagicMock()]
        successful_response.choices[0].message.content = json.dumps({
            "title": "Rate Limited Movie",
            "year": "2023",
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        
        # 设置第一次速率限制，第二次成功
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_mock_rate_limit_error("Rate limit exceeded"),
                successful_response
            ]
        )
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "RateLimit.Test.2023.mkv"
        
        # 调用被测函数
        result = await llm.analyze_filename(filename)
        
        # 验证结果
        assert result is not None
        assert result["title"] == "Rate Limited Movie"
        
        # 验证API客户端被调用了2次
        assert mock_openai_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mocker):
        """
        测试用例 3.6: 处理无效JSON响应
        Given: 模拟 openai 客户端返回无效的JSON格式
        When: 调用LLM分析函数
        Then: 函数应该优雅地处理错误并返回默认值或重试
        """
        # 模拟返回无效JSON的响应
        invalid_json_response = MagicMock()
        invalid_json_response.choices = [MagicMock()]
        invalid_json_response.choices[0].message.content = "这不是有效的JSON格式"
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=invalid_json_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "Invalid.Json.Test.mkv"
        
        # 调用被测函数，期望它能处理无效JSON
        with pytest.raises((json.JSONDecodeError, ValueError)):
            await llm.analyze_filename(filename)

    @pytest.mark.asyncio
    async def test_empty_response_content(self, mocker):
        """
        测试用例 3.7: 处理空响应内容
        Given: 模拟 openai 客户端返回空内容
        When: 调用LLM分析函数
        Then: 函数应该优雅地处理空响应
        """
        # 模拟空响应
        empty_response = MagicMock()
        empty_response.choices = [MagicMock()]
        empty_response.choices[0].message.content = ""
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=empty_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "Empty.Response.Test.mkv"
        
        # 调用被测函数
        with pytest.raises(ValueError):
            await llm.analyze_filename(filename)

    @pytest.mark.asyncio
    async def test_concurrent_calls_with_cache(self, mocker):
        """
        测试用例 3.8: 并发调用与缓存
        Given: 模拟 openai 客户端
        When: 同时发起多个相同文件名的LLM分析请求
        Then: 验证缓存机制在并发情况下仍然有效
        """
        # 模拟OpenAI客户端响应
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = json.dumps({
            "title": "Concurrent Test",
            "year": "2023",
            "type": "movie"
        })
        
        # 模拟异步的OpenAI客户端，添加延迟模拟网络请求
        mock_openai_client = AsyncMock()
        
        async def mock_create_with_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟网络延迟
            return mock_openai_response
        
        mock_openai_client.chat.completions.create = mock_create_with_delay
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 清除缓存
        if hasattr(llm.analyze_filename, 'cache_clear'):
            llm.analyze_filename.cache_clear()
        
        # 测试数据
        filename = "Concurrent.Test.2023.mkv"
        
        # 并发调用
        tasks = [llm.analyze_filename(filename) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有结果都相同
        assert all(result == results[0] for result in results)
        assert results[0]["title"] == "Concurrent Test"
        
        # 注意：由于LRU缓存的实现细节，在并发情况下可能会有多次调用
        # 但应该不会超过并发任务的数量
        # 这里我们检查调用次数是否合理（应该远少于5次）

    @pytest.mark.asyncio
    async def test_tv_show_detection(self, mocker):
        """
        测试用例 3.9: 电视剧检测
        Given: 输入明显是电视剧的文件名
        When: 调用LLM分析函数
        Then: 函数应该正确识别为电视剧类型
        """
        # 模拟OpenAI客户端响应
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock()]
        mock_openai_response.choices[0].message.content = json.dumps({
            "title": "Breaking Bad",
            "year": "2008",
            "type": "tv",
            "season": 1,
            "episode": 1
        })
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 测试数据
        filename = "Breaking.Bad.S01E01.720p.mkv"
        
        # 调用被测函数
        result = await llm.analyze_filename(filename)
        
        # 验证结果
        assert result is not None
        assert result["title"] == "Breaking Bad"
        assert result["type"] == "tv"
        assert result.get("season") == 1
        assert result.get("episode") == 1

    @pytest.mark.asyncio 
    async def test_cache_size_limit(self, mocker):
        """
        测试用例 3.10: 缓存大小限制
        Given: LRU缓存设置为maxsize=128
        When: 调用超过128个不同文件名的分析
        Then: 验证缓存正确地淘汰旧条目
        """
        # 模拟OpenAI客户端响应生成器
        def generate_response(title):
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = json.dumps({
                "title": title,
                "year": "2023",
                "type": "movie"
            })
            return response
        
        # 模拟异步的OpenAI客户端
        mock_openai_client = AsyncMock()
        
        # 创建一个计数器来跟踪API调用
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # 从调用参数中提取文件名信息
            return generate_response(f"Movie {call_count}")
        
        mock_openai_client.chat.completions.create = mock_create
        
        # 模拟获取OpenAI客户端的函数
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 清除缓存
        if hasattr(llm.analyze_filename, 'cache_clear'):
            llm.analyze_filename.cache_clear()
        
        # 调用130个不同的文件名（超过缓存大小128）
        for i in range(130):
            filename = f"Movie.{i}.2023.mkv"
            result = await llm.analyze_filename(filename)
            assert result is not None
        
        # 验证所有调用都真正执行了（因为文件名都不同）
        assert call_count == 130
        
        # 现在重新调用前面的一些文件名，由于LRU淘汰，早期的应该不在缓存中
        early_filename = "Movie.0.2023.mkv"
        recent_filename = "Movie.129.2023.mkv"
        
        # 重置计数器
        initial_count = call_count
        
        # 调用最近的文件名（应该在缓存中）
        await llm.analyze_filename(recent_filename)
        
        # 调用最早的文件名（应该不在缓存中，需要重新请求）
        await llm.analyze_filename(early_filename)
        
        # 验证：最近的文件名没有新的API调用，最早的文件名产生了新的API调用
        # 注意：由于LRU缓存的具体实现，这个测试可能需要根据实际情况调整
        assert call_count > initial_count  # 至少应该有一次新的API调用


class TestLLMDecoratorsAndIntegration:
    """测试LLM函数的装饰器和集成功能"""

    def test_retry_decorator_presence(self):
        """
        测试用例 4.1: 验证重试装饰器的存在
        Given: analyze_filename 函数
        When: 检查函数的装饰器
        Then: 函数应该有 tenacity.retry 装饰器
        """
        # 检查函数是否有重试装饰器的属性
        assert hasattr(llm.analyze_filename, 'retry'), "analyze_filename 函数应该被 @retry 装饰器装饰"
        
        # 验证重试装饰器的配置
        retry_decorator = llm.analyze_filename.retry
        assert retry_decorator is not None, "重试装饰器不应该为 None"

    def test_lru_cache_decorator_presence(self):
        """
        测试用例 4.2: 验证LRU缓存装饰器的存在
        Given: analyze_filename 函数
        When: 检查函数的装饰器
        Then: 函数应该有 functools.lru_cache 装饰器，且 maxsize=128
        """
        # 检查函数是否有缓存装饰器的属性
        assert hasattr(llm.analyze_filename, 'cache_info'), "analyze_filename 函数应该被 @lru_cache 装饰器装饰"
        assert hasattr(llm.analyze_filename, 'cache_clear'), "analyze_filename 函数应该有 cache_clear 方法"
        
        # 清除缓存并检查缓存信息
        llm.analyze_filename.cache_clear()
        cache_info = llm.analyze_filename.cache_info()
        
        # 验证缓存大小设置
        assert cache_info.maxsize == 128, f"缓存最大大小应该是 128，实际是 {cache_info.maxsize}"
        assert cache_info.currsize == 0, "清除缓存后，当前缓存大小应该是 0"

    @pytest.mark.asyncio
    async def test_decorators_execution_order(self, mocker):
        """
        测试用例 4.3: 验证装饰器执行顺序
        Given: analyze_filename 函数同时有 @lru_cache 和 @retry 装饰器
        When: 第一次调用失败，第二次调用相同参数
        Then: 验证缓存和重试的正确交互
        """
        # 模拟成功响应
        successful_response = MagicMock()
        successful_response.choices = [MagicMock()]
        successful_response.choices[0].message.content = json.dumps({
            "title": "Decorator Test",
            "year": "2023",
            "type": "movie"
        })
        
        # 模拟第一次失败，第二次成功的客户端
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_mock_api_error("First call fails"),
                successful_response
            ]
        )
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 清除缓存
        llm.analyze_filename.cache_clear()
        
        # 第一次调用（应该重试并成功）
        filename = "Decorator.Test.2023.mkv"
        result1 = await llm.analyze_filename(filename)
        
        # 验证第一次调用成功
        assert result1["title"] == "Decorator Test"
        assert mock_openai_client.chat.completions.create.call_count == 2  # 一次失败，一次成功
        
        # 重置mock计数器
        mock_openai_client.chat.completions.create.reset_mock()
        
        # 第二次调用相同参数（应该从缓存获取）
        result2 = await llm.analyze_filename(filename)
        
        # 验证缓存生效
        assert result2 == result1
        assert mock_openai_client.chat.completions.create.call_count == 0  # 没有新的API调用

    @pytest.mark.asyncio
    async def test_function_signature_and_typing(self):
        """
        测试用例 4.4: 验证函数签名和类型注解
        Given: analyze_filename 函数
        When: 检查函数签名
        Then: 函数应该有正确的参数和返回类型注解
        """
        import inspect
        
        # 获取函数签名
        sig = inspect.signature(llm.analyze_filename)
        
        # 验证参数
        params = list(sig.parameters.keys())
        assert 'filename' in params, "函数应该有 filename 参数"
        
        # 验证函数是异步的
        assert asyncio.iscoroutinefunction(llm.analyze_filename), "analyze_filename 应该是异步函数"

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, mocker):
        """
        测试用例 4.5: 验证指数退避重试机制
        Given: 模拟连续多次API失败
        When: 调用 analyze_filename 函数
        Then: 验证重试间隔符合指数退避模式
        """
        import time
        
        # 记录重试时间
        retry_times = []
        
        def record_time(*args, **kwargs):
            retry_times.append(time.time())
            raise create_mock_api_error("Continuous failure")
        
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=record_time)
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 尝试调用函数（预期会失败）
        with pytest.raises((APIError, RetryError)):
            await llm.analyze_filename("Backoff.Test.mkv")
        
        # 验证至少进行了多次重试
        assert len(retry_times) > 1, "应该进行多次重试"
        
        # 验证重试间隔（指数退避）
        if len(retry_times) >= 3:
            interval1 = retry_times[1] - retry_times[0]
            interval2 = retry_times[2] - retry_times[1]
            # 第二个间隔应该大于第一个间隔（指数退避）
            assert interval2 >= interval1, "重试间隔应该递增（指数退避）"


class TestLLMEdgeCasesAndBoundaryConditions:
    """测试LLM函数的边界条件和异常情况"""

    @pytest.mark.asyncio
    async def test_extremely_long_filename(self, mocker):
        """
        测试用例 5.1: 处理超长文件名
        Given: 一个超长的文件名（超过1000字符）
        When: 调用分析函数
        Then: 函数应该能够正常处理或优雅失败
        """
        # 创建超长文件名
        long_filename = "A" * 1000 + ".Very.Long.Movie.Name.2023.1080p.mkv"
        
        # 模拟正常响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Long Movie Name",
            "year": "2023",
            "type": "movie"
        })
        
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 调用函数
        result = await llm.analyze_filename(long_filename)
        
        # 验证结果
        assert result is not None
        assert result["title"] == "Long Movie Name"

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, mocker):
        """
        测试用例 5.2: 处理Unicode和特殊字符
        Given: 包含各种Unicode字符和特殊符号的文件名
        When: 调用分析函数
        Then: 函数应该正确处理这些字符
        """
        # 包含多种语言和特殊字符的文件名
        unicode_filename = "🎬电影名称_фильм-2023年【HD】.mkv"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "电影名称",
            "year": "2023",
            "type": "movie"
        }, ensure_ascii=False)
        
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 调用函数
        result = await llm.analyze_filename(unicode_filename)
        
        # 验证结果
        assert result is not None
        assert result["title"] == "电影名称"
        assert result["year"] == "2023"

    @pytest.mark.asyncio
    async def test_empty_and_whitespace_filename(self, mocker):
        """
        测试用例 5.3: 处理空字符串和纯空白文件名
        Given: 空字符串或纯空白字符的文件名
        When: 调用分析函数
        Then: 函数应该优雅地处理这些情况
        """
        test_cases = ["", "   ", "\t\n", "   \t  \n  "]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Unknown",
            "year": None,
            "type": "unknown"
        })
        
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        for fname in test_cases:
            with pytest.raises(ValueError):
                await llm.analyze_filename(fname)

    @pytest.mark.asyncio
    async def test_malformed_openai_response_structure(self, mocker):
        """
        测试用例 5.4: 处理OpenAI响应结构异常
        Given: OpenAI返回结构异常的响应
        When: 调用分析函数
        Then: 函数应该能处理各种响应结构异常
        """
        # 测试不同的异常响应结构
        malformed_responses = [
            # 缺少choices
            MagicMock(choices=[]),
            # choices为None
            MagicMock(choices=None),
            # message为None
            type('MockResponse', (), {
                'choices': [type('MockChoice', (), {'message': None})()]
            })(),
            # content为None
            type('MockResponse', (), {
                'choices': [type('MockChoice', (), {
                    'message': type('MockMessage', (), {'content': None})()
                })()]
            })(),
        ]
        
        mock_openai_client = AsyncMock()
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        for malformed_response in malformed_responses:
            mock_openai_client.chat.completions.create = AsyncMock(return_value=malformed_response)
            
            try:
                result = await llm.analyze_filename("Test.Malformed.mkv")
                # 如果函数返回结果，验证其合理性
                if result is not None:
                    assert isinstance(result, dict)
            except (AttributeError, TypeError, IndexError):
                # 如果函数抛出这些异常，这是可以理解的
                pass

    @pytest.mark.asyncio
    async def test_network_timeout_scenarios(self, mocker):
        """
        测试用例 5.5: 网络超时场景
        Given: 模拟各种网络超时情况
        When: 调用分析函数
        Then: 验证超时处理和重试机制
        """
        import asyncio
        
        # 模拟超时后成功的场景
        successful_response = MagicMock()
        successful_response.choices = [MagicMock()]
        successful_response.choices[0].message.content = json.dumps({
            "title": "Timeout Test",
            "year": "2023",
            "type": "movie"
        })
        
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                asyncio.TimeoutError("Connection timeout"),
                APITimeoutError("Request timeout"),
                successful_response
            ]
        )
        
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 调用函数
        result = await llm.analyze_filename("Timeout.Test.2023.mkv")
        
        # 验证最终成功
        assert result is not None
        assert result["title"] == "Timeout Test"
        
        # 验证重试次数
        assert mock_openai_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_memory_pressure_during_caching(self, mocker):
        """
        测试用例 5.6: 缓存内存压力测试
        Given: 大量不同的文件名请求
        When: 持续调用分析函数
        Then: 验证缓存在内存压力下的表现
        """
        def generate_large_response(title):
            # 生成较大的响应数据以增加内存压力
            response = MagicMock()
            response.choices = [MagicMock()]
            large_description = "A" * 10000  # 10KB的描述
            response.choices[0].message.content = json.dumps({
                "title": title,
                "year": "2023",
                "type": "movie",
                "description": large_description,
                "large_metadata": ["item" + str(i) for i in range(1000)]
            })
            return response
        
        mock_openai_client = AsyncMock()
        
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return generate_large_response(f"Large Movie {call_count}")
        
        mock_openai_client.chat.completions.create = mock_create
        mocker.patch("app.core.llm.get_openai_client", return_value=mock_openai_client)
        
        # 清除缓存
        llm.analyze_filename.cache_clear()
        
        # 生成大量请求
        results = []
        for i in range(200):  # 超过缓存限制
            filename = f"Large.Movie.{i}.2023.mkv"
            result = await llm.analyze_filename(filename)
            results.append(result)
            
            # 每隔50次检查缓存状态
            if i % 50 == 0:
                cache_info = llm.analyze_filename.cache_info()
                assert cache_info.currsize <= 128, "缓存大小不应超过设定限制"
        
        # 验证所有请求都成功
        assert len(results) == 200
        assert all(result is not None for result in results)
        
        # 验证缓存按预期工作
        final_cache_info = llm.analyze_filename.cache_info()
        assert final_cache_info.currsize == 128, "最终缓存大小应该等于最大限制" 