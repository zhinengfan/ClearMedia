"""LLM交互模块 (llm.py)
使用 openai 客户端进行文件名分析
"""
import re
import json
import asyncio
from typing import Dict, Union
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from async_lru import alru_cache
from openai import (
    AsyncOpenAI,
    APIError,
    APITimeoutError,
    RateLimitError,
)
from loguru import logger
from ..config import settings as _settings

# 缓存OpenAI客户端实例
_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """获取或创建OpenAI客户端实例"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=_settings.OPENAI_API_KEY,
            base_url=_settings.OPENAI_API_BASE,
        )
    return _openai_client

@alru_cache(maxsize=128)
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
    # 日志记录缓存未命中，便于调试
    logger.info(f"LLM Cache Miss: Calling LLM API for filename: '{filename}'")

    # 输入验证
    if not filename or not filename.strip():
        raise ValueError("文件名不能为空")
        
    # 准备系统提示和用户提示
    system_prompt = """你是一个专业的媒体文件名分析助手。从影视文件名提取信息，输出JSON包含：title(必填), year(可选), type(必填), season/episode(仅电视剧),
**核心规则：**
1. 清洗干扰项：移除分辨率/编码/版本标识(v2等)/扩展名，特殊字符转空格
2. 标题：取最长文字部分，清除尾随数字（如"沙尘暴07"→"沙尘暴"）
3. 类型检测：
   - 有季集标识(S/E/季/集)或结尾≥2位孤立数字 → `"tv"`
   - 否则 → `"movie"`
4. 季集处理：
   - 无明确季 → season=1
   - 结尾数字 → episode（如"07v2"→7）
5. 年份：仅提取1900-2099的4位数

**输出示例：**
{"title": "Breaking Bad", "type": "tv", "season": 1, "episode": 7}

**严格约束：**
- 电视剧必含season/episode
- 电影禁止出现season/episode
- 无年份时省略year字段"""

    user_prompt = f"请分析这个文件名: {filename}"
    
    # 获取OpenAI客户端
    client = get_openai_client()
    
    # 构造请求参数
    request_params = {
        "model": _settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
    }

    # 仅当使用官方 OpenAI 端点时才使用 response_format
    if "api.openai.com" in _settings.OPENAI_API_BASE:
        request_params["response_format"] = {"type": "json_object"}

    # 调用API
    try:
        response = await client.chat.completions.create(**request_params)
        
        # 验证响应
        if not response.choices or not response.choices[0].message or response.choices[0].message.content is None:
            raise ValueError("LLM返回了无效的响应结构")
            
        raw_content = response.choices[0].message.content.strip()
        if not raw_content:
            raise ValueError("LLM返回了空响应")
            
        # 优化了JSON解析逻辑
        # 很多模型会在JSON前后添加```json ... ```标记，先移除它们
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]
        
        # 移除 <think>...</think> 标签包围的内容
        think_pattern = r'<think>.*?</think>\s*'
        raw_content = re.sub(think_pattern, '', raw_content, flags=re.DOTALL)
        
        # 找到第一个 { 和最后一个 }，提取它们之间的内容
        first_brace = raw_content.find("{")
        last_brace = raw_content.rfind("}")
        if first_brace == -1 or last_brace == -1:
            raise json.JSONDecodeError("在LLM响应中未找到JSON对象", raw_content, 0)
        
        json_string = raw_content[first_brace : last_brace + 1].strip()
        result = json.loads(json_string)
        
        # 验证必填字段
        if not result.get("title"):
            raise ValueError("LLM返回的结果缺少title字段")
            
        if "type" not in result or result["type"] not in ["movie", "tv"]:
            result["type"] = "movie"  # 如果type无效或不存在，默认为电影类型
        
        logger.info(f"成功分析文件名: '{filename}' -> {result}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"LLM返回的不是有效JSON: '{filename}', 响应内容: '{raw_content}', 错误: {e}")
        raise
    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.warning(f"OpenAI API错误，将重试: '{filename}', 错误: {e}")
        raise
    except Exception as e:
        logger.error(f"分析文件名时发生未知错误: '{filename}', 错误类型: {type(e).__name__}, 错误: {e}")
        raise 