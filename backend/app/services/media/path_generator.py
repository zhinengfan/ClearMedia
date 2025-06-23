"""媒体文件路径生成模块

负责根据媒体信息生成标准的目标路径
"""

from pathlib import Path


def sanitize_title(title: str) -> str:
    """清理标题中的特殊字符
    
    Args:
        title: 原始标题
        
    Returns:
        str: 清理后的标题，只保留字母数字、空格、连字符和下划线
    """
    return "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()


def generate_new_path(
    media_info: dict, 
    llm_guess: dict | None,
    original_filepath: str, 
    target_dir: Path
) -> Path:
    """根据媒体信息生成标准的目标路径
    
    Args:
        media_info: TMDB返回的媒体信息
        llm_guess: LLM分析结果，用于获取季/集信息
        original_filepath: 原始文件路径
        target_dir: 目标目录
        
    Returns:
        Path: 生成的新文件路径
    """
    # 获取原始文件的扩展名
    original_path = Path(original_filepath)
    file_extension = original_path.suffix
    
    # 根据媒体类型生成路径
    if "name" in media_info:  # 电视剧
        title = media_info["name"]
        year = ""
        if "first_air_date" in media_info and media_info["first_air_date"]:
            year = media_info["first_air_date"][:4]  # 提取年份
        
        # 清理标题中的特殊字符
        clean_title = sanitize_title(title)
        
        if year:
            folder_name = f"{clean_title} ({year})"
        else:
            folder_name = clean_title
            
        # 从 LLM 结果中获取季和集信息
        season = 1  # 默认第一季
        episode = None
        if llm_guess:
            season = llm_guess.get("season", 1)
            episode = llm_guess.get("episode")
        
        if episode is not None:
            filename = f"{clean_title} S{season:02d}E{episode:02d}{file_extension}"
        else:
            # 如果没有剧集信息，则使用原始文件名，防止覆盖
            filename = f"{folder_name}{file_extension}"

        return target_dir / "TV Shows" / folder_name / filename
        
    else:  # 电影
        title = media_info.get("title", "Unknown")
        year = ""
        if "release_date" in media_info and media_info["release_date"]:
            year = media_info["release_date"][:4]  # 提取年份
        
        # 清理标题中的特殊字符
        clean_title = sanitize_title(title)
        
        if year:
            filename = f"{clean_title} ({year}){file_extension}"
        else:
            filename = f"{clean_title}{file_extension}"
            
        return target_dir / "Movies" / filename 