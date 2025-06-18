"""文件系统硬链接器模块

提供安全的硬链接创建功能，包含完整的错误处理和状态返回。

本模块遵循 MVP 文档规范，实现文件系统硬链接的创建操作，
支持跨设备检测、路径冲突检查和权限错误处理。

Example:
    >>> from pathlib import Path
    >>> from app.core.linker import create_hardlink, LinkResult
    >>>
    >>> source = Path("/source/movie.mkv")
    >>> target = Path("/target/Movie (2023).mkv")
    >>> result = create_hardlink(source, target)
    >>>
    >>> if result == LinkResult.LINK_SUCCESS:
    >>>     print("硬链接创建成功")
"""

from __future__ import annotations

import errno
import os
from enum import StrEnum
from pathlib import Path

from loguru import logger


class LinkResult(StrEnum):
    """硬链接创建结果枚举

    定义硬链接操作的所有可能返回状态，用于精确的错误处理和状态反馈。
    """

    LINK_SUCCESS = "success"
    """成功创建硬链接"""

    LINK_FAILED_CONFLICT = "conflict"
    """目标路径已存在文件，创建失败"""

    LINK_FAILED_CROSS_DEVICE = "cross_device"
    """源文件和目标路径在不同文件系统，无法创建硬链接"""

    LINK_FAILED_NO_SOURCE = "no_source"
    """源文件不存在或不是常规文件"""

    LINK_FAILED_UNKNOWN = "unknown"
    """其他未知系统错误"""


def create_hardlink(source_path: Path, destination_path: Path) -> LinkResult:
    """安全地创建硬链接

    按照 MVP 文档逻辑实现硬链接创建，包含完整的前置检查、
    目录创建和错误处理机制。

    Args:
        source_path: 源文件的绝对路径，必须是现有的常规文件
        destination_path: 目标硬链接的绝对路径，不能已存在

    Returns:
        LinkResult: 操作结果枚举
            - LINK_SUCCESS: 硬链接创建成功
            - LINK_FAILED_NO_SOURCE: 源文件不存在或不是文件
            - LINK_FAILED_CONFLICT: 目标路径已存在
            - LINK_FAILED_CROSS_DEVICE: 跨文件系统错误
            - LINK_FAILED_UNKNOWN: 其他系统错误

    Raises:
        无直接异常抛出，所有错误通过返回值表示

    Note:
        实现步骤严格按照 MVP 文档要求：
        1. 验证源文件存在性和类型
        2. 检查目标路径冲突
        3. 确保目标目录存在
        4. 执行 os.link 操作
        5. 捕获并分类所有可能的 OSError
    """
    logger.debug(f"硬链接操作开始: {source_path} -> {destination_path}")

    # 步骤 1: 前置检查 - 验证源文件
    if not source_path.exists():
        logger.warning(f"源文件不存在: {source_path}")
        return LinkResult.LINK_FAILED_NO_SOURCE

    if not source_path.is_file():
        logger.warning(f"源路径不是常规文件: {source_path}")
        return LinkResult.LINK_FAILED_NO_SOURCE

    # 步骤 2: 前置检查 - 目标路径冲突检测
    if destination_path.exists():
        logger.warning(f"目标路径已存在，无法创建硬链接: {destination_path}")
        return LinkResult.LINK_FAILED_CONFLICT

    # 步骤 3: 确保目标目录结构存在
    target_parent = destination_path.parent
    try:
        target_parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"目标目录已确保存在: {target_parent}")
    except OSError as e:
        logger.error(f"创建目标目录失败: {target_parent}, 错误: {e}")
        return LinkResult.LINK_FAILED_UNKNOWN

    # 步骤 4: 执行硬链接创建操作
    try:
        os.link(source_path, destination_path)
        logger.success(f"硬链接创建成功: {source_path} -> {destination_path}")
        return LinkResult.LINK_SUCCESS

    except OSError as e:
        # 步骤 5: 错误分类处理
        if e.errno == errno.EXDEV:
            # 跨设备/文件系统错误
            logger.warning(
                f"跨设备链接失败，源和目标在不同文件系统: {source_path} -> {destination_path}"
            )
            return LinkResult.LINK_FAILED_CROSS_DEVICE
        else:
            # 其他未知系统错误
            logger.error(f"硬链接创建时发生未知错误: {e} (errno: {e.errno})")
            return LinkResult.LINK_FAILED_UNKNOWN
