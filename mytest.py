import asyncio
from pprint import pprint

# -------------- 导入我们要测试的封装 ---------------------------
from backend.app.core import tmdb as tmdb_core    # 为避免同名冲突取别名

# -------------- 写一个异步 main 函数 --------------------------
async def main():
    # ① 先搜索。标题、年份都可改成你想试的任何内容
    movie = await tmdb_core.search_movie(
        {"title": "未闻花名"}
    )
    pprint(movie)  # 直接打印 movie 对象，不需要额外的字符串前缀

    if movie:
        # ② 再拿详情
        details = await tmdb_core.get_movie_details(movie["id"])
        print("Details title:", details["title"])
        print("Overview:", details["overview"][:150], "...")
        print("Runtime:", details["runtime"], "minutes")

# -------------- 直接跑 --------------------------
asyncio.run(main())



# from backend.app.core.llm import analyze_filename

# async def main():
#     result = await analyze_filename('[云光字幕组] mono女孩  Mono [01][简体双语][1080p]招募翻译.mp4')
#     pprint(result)

# asyncio.run(main())
