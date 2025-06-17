"""LLM交互模块 (llm.py)
使用 openai 客户端进行文件名分析
"""

import json
import asyncio
from typing import Dict, Union
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import (
    AsyncOpenAI,
    APIError,
    APITimeoutError,
    RateLimitError,
)
from loguru import logger

# 缓存OpenAI客户端实例
_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """获取或创建OpenAI客户端实例"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI()
    return _openai_client

# 创建一个简单的异步缓存装饰器
_cache = {}
_cache_stats = {'hits': 0, 'misses': 0, 'maxsize': 128, 'currsize': 0}

def async_lru_cache(maxsize: int = 128):
    """异步LRU缓存装饰器"""
    def decorator(func):
        cache = {}
        cache_info = {'hits': 0, 'misses': 0, 'maxsize': maxsize, 'currsize': 0}
        
        async def wrapper(*args, **kwargs):
            # 创建缓存键
            key = str(args) + str(sorted(kwargs.items()))
            
            if key in cache:
                cache_info['hits'] += 1
                return cache[key]
            
            # 如果缓存已满，删除最老的条目（简单FIFO，不是真正的LRU）
            if len(cache) >= maxsize:
                oldest_key = next(iter(cache))
                del cache[oldest_key]
                cache_info['currsize'] -= 1
            
            # 调用原函数并缓存结果
            try:
                result = await func(*args, **kwargs)
                cache[key] = result
                cache_info['misses'] += 1
                cache_info['currsize'] += 1
                return result
            except Exception as e:
                # 不缓存异常结果
                raise e
        
        # 添加缓存管理方法
        def cache_clear():
            cache.clear()
            cache_info['hits'] = 0
            cache_info['misses'] = 0
            cache_info['currsize'] = 0
        
        def cache_info_func():
            from collections import namedtuple
            CacheInfo = namedtuple('CacheInfo', ['hits', 'misses', 'maxsize', 'currsize'])
            return CacheInfo(**cache_info)
        
        wrapper.cache_clear = cache_clear
        wrapper.cache_info = cache_info_func
        wrapper.__wrapped__ = func
        
        return wrapper
    return decorator

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    retry=(
        retry_if_exception_type(APIError) |
        retry_if_exception_type(APITimeoutError) |
        retry_if_exception_type(RateLimitError) |
        retry_if_exception_type(TimeoutError) |
        retry_if_exception_type(asyncio.TimeoutError)
    ),
)
@async_lru_cache(maxsize=128)
async def analyze_filename(filename: str) -> Dict[str, Union[str, int, None]]:
    """
    使用LLM分析文件名，提取标题、年份和类型等信息
    
    Args:
        filename: 需要分析的文件名
        
    Returns:
        Dict[str, Union[str, int, None]]: 包含以下字段的字典:
            - title: 影视作品标题
            - year: 发行年份(可能为None)
            - type: 类型('movie'或'tv')
            - season: 季数(仅电视剧，可能为None)
            - episode: 集数(仅电视剧，可能为None)
            
    Raises:
        ValueError: 当文件名为空或仅包含空白字符时
        json.JSONDecodeError: 当LLM返回的不是有效JSON时
    """
    # 输入验证
    if not filename or not filename.strip():
        raise ValueError("文件名不能为空")
        
    # 准备系统提示和用户提示
    system_prompt = """你是一个专业的文件名分析助手。你的任务是从电影或电视剧文件名中提取关键信息。
请将分析结果以JSON格式返回，包含以下字段:
- title: 影视作品标题(必填)
- year: 发行年份(如果能识别)
- type: 类型，使用'movie'表示电影，'tv'表示电视剧
- season: 季数(仅电视剧)
- episode: 集数(仅电视剧)

示例输出:
{
    "title": "Breaking Bad",
    "year": 2008,
    "type": "tv",
    "season": 1,
    "episode": 1
}"""

    user_prompt = f"请分析这个文件名: {filename}"
    
    # 获取OpenAI客户端
    client = get_openai_client()
    
    # 调用API
    try:
        response = await client.chat.completions.create(
            model="gpt-4",  # 使用最新可用的GPT-4模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # 降低随机性，保持输出一致性
            response_format={"type": "json_object"},  # 强制JSON输出
        )
        
        # 验证响应
        if not response.choices:
            raise AttributeError("响应中缺少choices字段")
        
        if not response.choices[0].message:
            raise AttributeError("响应中缺少message字段")
            
        if response.choices[0].message.content is None:
            raise AttributeError("响应中缺少content字段")
            
        if response.choices[0].message.content == "":
            raise ValueError("LLM返回了空响应")
            
        # 解析JSON
        result = json.loads(response.choices[0].message.content)
        
        # 验证必填字段
        if not result.get("title"):
            raise ValueError("LLM返回的结果缺少title字段")
            
        if "type" not in result:
            result["type"] = "movie"  # 默认为电影类型
        
        logger.info(f"成功分析文件名: {filename} -> {result}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM返回的不是有效JSON: {filename}, 错误: {e}")
        raise
    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.warning(f"OpenAI API错误，将重试: {filename}, 错误: {e}")
        raise
    except Exception as e:
        logger.error(f"分析文件名时发生未知错误: {filename}, 错误: {e}")
        raise 