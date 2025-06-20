import asyncio
from loguru import logger
import tmdbsimple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from async_lru import alru_cache
from typing import Optional, Dict, Any
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


@alru_cache(maxsize=128)
@retry(**retry_config)
async def search_movie_by_title_and_year(title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    根据标题和年份搜索电影信息
    
    Args:
        title (str): 电影标题
        year (Optional[int]): 发行年份，可选
    
    Returns:
        Optional[Dict[str, Any]]: 找到的电影信息，如果未找到则返回None
    """
    # 日志记录缓存未命中，便于调试
    logger.info(f"TMDB Cache Miss: Calling TMDB API for search_movie: title='{title}', year={year}")
    
    async with TMDB_SEMAPHORE:
        try:
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
                logger.info(f"成功搜索电影: {title} ({year if year else '无年份'}) -> {search.results[0].get('title', 'N/A')} ({search.results[0].get('release_date')[:4] if search.results[0].get('release_date') else 'N/A'})")
                return search.results[0]
            
            logger.info(f"未找到电影: {title} ({year if year else '无年份'})")
            return None
            
        except Exception as e:
            logger.error(f"搜索电影时出错: {str(e)}")
            raise


async def search_movie(llm_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    搜索电影信息 - 兼容性包装函数
    
    Args:
        llm_data (Dict[str, Any]): 包含电影信息的字典，必须包含title，可选包含year
    
    Returns:
        Optional[Dict[str, Any]]: 找到的电影信息，如果未找到则返回None
    """
    title = llm_data.get("title")
    if not title:
        raise ValueError("llm_data必须包含title字段")
    
    year = None
    if "year" in llm_data and llm_data["year"]:
        try:
            year = int(llm_data["year"])
        except (ValueError, TypeError):
            logger.warning(f"无效的年份格式: {llm_data['year']}")
    
    return await search_movie_by_title_and_year(title, year)


@alru_cache(maxsize=256)
@retry(**retry_config)
async def get_movie_details(movie_id: int) -> Dict[str, Any]:
    """
    获取电影详细信息
    
    Args:
        movie_id (int): TMDB电影ID
    
    Returns:
        Dict[str, Any]: 电影详细信息
    """
    # 日志记录缓存未命中，便于调试
    logger.info(f"TMDB Cache Miss: Calling TMDB API for get_movie_details: movie_id={movie_id}")
    
    async with TMDB_SEMAPHORE:
        try:
            # 使用asyncio.to_thread包装同步操作
            movie = tmdbsimple.Movies(movie_id)

            def _get_movie_info():
                # 返回 TMDB 原始信息字典，避免 MagicMock 属性问题
                return movie.info()
            
            movie_info = await asyncio.to_thread(_get_movie_info)

            logger.info(f"成功获取电影详情: movie_id={movie_id} -> {movie_info.get('title', 'N/A')}")
            return movie_info
            
        except Exception as e:
            logger.error(f"获取电影详情时出错: {str(e)}")
            raise


@alru_cache(maxsize=128)
@retry(**retry_config)
async def search_tv_by_title_and_year(title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    根据标题和年份搜索电视剧信息
    
    Args:
        title (str): 电视剧标题
        year (Optional[int]): 首播年份，可选
    
    Returns:
        Optional[Dict[str, Any]]: 找到的电视剧信息，如果未找到则返回None
    """
    # 日志记录缓存未命中，便于调试
    logger.info(f"TMDB Cache Miss: Calling TMDB API for search_tv: title='{title}', year={year}")
    
    async with TMDB_SEMAPHORE:
        try:
            # 使用asyncio.to_thread包装同步操作
            search = tmdbsimple.Search()
            
            def _search_tv():
                kwargs = {"query": title}
                if year:
                    kwargs["first_air_date_year"] = year
                search.tv(**kwargs)
                return search.results
            
            _ = await asyncio.to_thread(_search_tv)
            
            if search.results:
                logger.info(f"成功搜索电视剧: {title} ({year if year else '无年份'}) -> {search.results[0].get('name', 'N/A')} ({search.results[0].get('first_air_date')[:4] if search.results[0].get('first_air_date') else 'N/A'})")
                return search.results[0]
            
            logger.info(f"未找到电视剧: {title} ({year if year else '无年份'})")
            return None
            
        except Exception as e:
            logger.error(f"搜索电视剧时出错: {str(e)}")
            raise


async def search_media(llm_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    根据 LLM 分析结果搜索媒体信息（电影或电视剧）
    
    Args:
        llm_data (Dict[str, Any]): LLM 分析的结果，包含 title, type, year 等字段
    
    Returns:
        Optional[Dict[str, Any]]: 找到的媒体信息，包含 tmdb_id 和 media_type 字段
    """
    title = llm_data.get("title")
    if not title:
        raise ValueError("llm_data必须包含title字段")
    
    media_type = llm_data.get("type", "movie")
    year = None
    if "year" in llm_data and llm_data["year"]:
        try:
            year = int(llm_data["year"])
        except (ValueError, TypeError):
            logger.warning(f"无效的年份格式: {llm_data['year']}")
    
    try:
        if media_type == "tv":
            result = await search_tv_by_title_and_year(title, year)
            if result:
                return {
                    "tmdb_id": result["id"],
                    "media_type": "tv",
                    "processed_data": result
                }
        else:  # movie or fallback
            result = await search_movie_by_title_and_year(title, year)
            if result:
                return {
                    "tmdb_id": result["id"],
                    "media_type": "movie", 
                    "processed_data": result
                }
        
        logger.warning(f"未在TMDB中找到匹配的媒体: {title} ({media_type})")
        return None
        
    except Exception as e:
        logger.error(f"搜索媒体时出错: {title} ({media_type}) - {str(e)}")
        raise 