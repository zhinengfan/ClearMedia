"""
Pydantic模型（Schemas）模块

定义用于API请求/响应数据校验、序列化和文档生成的Pydantic模型。
与数据库模型（models.py）分离，以实现更灵活的API接口定义。
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime



# 基础媒体文件信息（用于列表项）
class MediaFileItem(BaseModel):
    id: int
    inode: int
    device_id: int
    original_filepath: str
    original_filename: str
    file_size: int
    status: str  # 使用 str 而不是 FileStatus，因为 FileStatus 不是真正的枚举
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# 媒体文件列表响应模型
class MediaFilesResponse(BaseModel):
    total: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool
    items: List[MediaFileItem]


# 完整的媒体文件详情模型
class MediaFileDetail(BaseModel):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    inode: int
    device_id: int
    original_filepath: str
    original_filename: str
    file_size: int
    status: str
    llm_guess: Optional[Dict] = None
    tmdb_id: Optional[int] = None
    media_type: Optional[str] = None
    processed_data: Optional[Dict] = None
    new_filepath: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    class Config:
        from_attributes = True


# 文件名建议响应模型
class SuggestionResponse(BaseModel):
    suggestions: List[str]


# 文件重试操作响应模型
class RetryResponse(BaseModel):
    message: str
    file_id: int
    previous_status: str
    current_status: str


# 配置获取响应模型
class ConfigGetResponse(BaseModel):
    config: Dict[str, Any]
    blacklist_keys: List[str]
    message: str


# 配置更新响应模型
class ConfigUpdateResponse(BaseModel):
    message: str
    config: Dict[str, Any]
    blacklist_keys: List[str]
    updated_keys: Optional[List[str]] = None
    rejected_keys: Optional[List[str]] = None 