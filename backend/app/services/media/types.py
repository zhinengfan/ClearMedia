"""媒体处理相关的数据结构和类型定义"""

from typing import NamedTuple


class ProcessResult(NamedTuple):
    """处理结果"""
    success: bool
    message: str
    media_file_id: int 