import asyncio
from loguru import logger
import tmdbsimple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..config import settings as _settings

# 依据配置更新并发限制 & API Key
TMDB_SEMAPHORE = asyncio.Semaphore(_settings.TMDB_CONCURRENCY)
tmdbsimple.API_KEY = _settings.TMDB_API_KEY
# 如果有语言需求
if hasattr(tmdbsimple, 'DEFAULT_LANGUAGE'):
    tmdbsimple.DEFAULT_LANGUAGE = _settings.TMDB_LANGUAGE

# 重试装饰器配置
retry_config = {
    'stop': stop_after_attempt(3),  # 最多尝试3次
    'wait': wait_exponential(multiplier=1, min=1, max=10),  # 指数退避策略
    'retry': retry_if_exception_type((
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError
    )),
    'reraise': True,  # 重试失败后抛出原始异常
}


@retry(**retry_config)
async def search_movie(llm_data):
    """
    搜索电影信息
    
    Args:
        llm_data (dict): 包含电影信息的字典，必须包含title，可选包含year
    
    Returns:
        dict: 找到的电影信息，如果未找到则返回None
    """
    async with TMDB_SEMAPHORE:
        try:
            title = llm_data.get("title")
            year = None
            
            if "year" in llm_data and llm_data["year"]:
                try:
                    year = int(llm_data["year"])
                except (ValueError, TypeError):
                    logger.warning(f"无效的年份格式: {llm_data['year']}")
            
            # 使用asyncio.to_thread包装同步操作
            search = tmdbsimple.Search()
            
            def _search_movie():
                kwargs = {"query": title}
                if year:
                    kwargs["year"] = year
                search.movie(**kwargs)
                return search.results
            
            _ = await asyncio.to_thread(_search_movie)
            
            if search.results:
                return search.results[0]
            
            logger.info(f"未找到电影: {title} ({year if year else '无年份'})")
            return None
            
        except Exception as e:
            logger.error(f"搜索电影时出错: {str(e)}")
            raise


@retry(**retry_config)
async def get_movie_details(movie_id):
    """
    获取电影详细信息
    
    Args:
        movie_id (int): TMDB电影ID
    
    Returns:
        dict: 电影详细信息
    """
    async with TMDB_SEMAPHORE:
        try:
            # 使用asyncio.to_thread包装同步操作
            movie = tmdbsimple.Movies(movie_id)

            def _get_movie_info():
                # 返回 TMDB 原始信息字典，避免 MagicMock 属性问题
                return movie.info()
            
            movie_info = await asyncio.to_thread(_get_movie_info)

            return movie_info
            
        except Exception as e:
            logger.error(f"获取电影详情时出错: {str(e)}")
            raise 