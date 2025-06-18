# ruff: noqa  # ← 这一行告诉 Ruff 跳过整个文件
# -------------- 导入我们要测试的封装 ---------------------------
# from backend.app.core import tmdb as tmdb_core    # 为避免同名冲突取别名

# # -------------- 写一个异步 main 函数 --------------------------
# async def main():
#     # ① 先搜索。标题、年份都可改成你想试的任何内容
#     movie = await tmdb_core.search_movie(
#         {"title": "未闻花名"}
#     )
#     pprint(movie)  # 直接打印 movie 对象，不需要额外的字符串前缀

#     if movie:
#         # ② 再拿详情
#         details = await tmdb_core.get_movie_details(movie["id"])
#         print("Details title:", details["title"])
#         print("Overview:", details["overview"][:150], "...")
#         print("Runtime:", details["runtime"], "minutes")

# # -------------- 直接跑 --------------------------
# asyncio.run(main())



# from backend.app.core.llm import analyze_filename

# async def main():
#     result = await analyze_filename('[云光字幕组] mono女孩  Mono [01][简体双语][1080p]招募翻译.mp4')
#     pprint(result)

# asyncio.run(main())

# from pathlib import Path
# from backend.app.core.linker import create_hardlink, LinkResult

# source = Path("/home/zz/media_sim/[云光字幕组] mono女孩  Mono [01][简体双语][1080p]招募翻译.mp4")
# target = Path("/home/zz/media_test/mono女孩- 01.mp4")
# result = create_hardlink(source, target)

# if result == LinkResult.LINK_SUCCESS:
#     print("硬链接创建成功")

# -------------- 扫描器快速测试 ---------------------------
"""
使用方法：
    uv run python mytest.py

要求：
1. 项目根目录已有 .env 文件，且至少包含
   - OPENAI_API_KEY
   - TMDB_API_KEY
   - SOURCE_DIR   # 要扫描的目录
   - TARGET_DIR   # 目标目录
2. 如果 .env 修改了 SOURCE_DIR / VIDEO_EXTENSIONS 等字段，脚本会自动读取。

脚本流程：
• 把 backend 目录加入 PYTHONPATH → 通过 `app.xxx` 导入内部模块  
• 自动建表 → 调用 scan_directory_once 完成一次扫描并打印结果
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
# 确保 backend 在 PYTHONPATH 中
sys.path.append(str(PROJECT_ROOT / "backend"))

from sqlmodel import Session

from app.config import settings          # 直接读取 .env
from app.db import create_db_and_tables, engine
from app.scanner import scan_directory_once


def main() -> None:
    create_db_and_tables()  # 若表不存在会自动创建

    allowed_exts = {
        ext.strip() for ext in settings.VIDEO_EXTENSIONS.split(",") if ext.strip()
    }

    with Session(engine) as session:
        new_files = scan_directory_once(
            session,
            settings.SOURCE_DIR,
            allowed_exts,
        )

    print(f"本次扫描共新增 {new_files} 个媒体文件")


if __name__ == "__main__":
    main()
