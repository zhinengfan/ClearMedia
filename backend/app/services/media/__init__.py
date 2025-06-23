"""媒体处理服务模块

重构为多个专职子模块：
- types: 数据结构和类型定义
- path_generator: 路径生成逻辑
- status_manager: 状态管理
- processor: 主处理协调器
- scanner: 文件扫描功能

为了保持向后兼容，重新导出关键符号
"""


from .processor import process_media_file
from .types import ProcessResult
from .path_generator import generate_new_path, sanitize_title
from .scanner import scan_directory_once, background_scanner_task
from . import status_manager

__all__ = [
    "process_media_file",
    "ProcessResult", 
    "generate_new_path",
    "sanitize_title",
    "scan_directory_once", 
    "background_scanner_task",
    "status_manager"
] 