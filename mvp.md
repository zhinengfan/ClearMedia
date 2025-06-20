### **项目蓝图：ClearMedia **

#### **1. 项目概述 (The "Why")**

*   **项目名称:** ClearMedia
*   **目标:** 开发一款智能媒体整理工具，利用LLM对不规范的媒体文件名进行识别，从TMDB获取准确元数据，并将其重命名/链接为媒体服务器的标准格式。
*   **服务对象:** 拥有NAS并熟悉Docker环境的家庭用户。
*   **核心价值:** 高识别率、自动化、非侵入式（支持硬链接保种）、易于部署。

#### **2. 最小可行产品 (MVP) 范围 (The "What")**

MVP的核心是一个纯后端服务，无Web前端界面，通过Docker运行。

*   **配置:** 通过项目根目录的`.env`文件进行配置。
*   **扫描:** 定时扫描用户指定的"源文件夹" (`SOURCE_DIR`)。
*   **文件标识:** 使用文件的`inode` + `device_id`作为唯一标识，避免重复处理。
*   **识别流程:**
    1.  对新文件，调用**LLM**进行智能分析，提取`标题`、`年份`和`类型`，并强制以JSON格式返回。
    2.  使用从LLM获取的信息，查询**TMDB API**以获得精确的官方媒体数据。
*   **文件操作:**
    *   **仅支持硬链接 (`hardlink`) 模式**。
    *   **冲突处理:** 若目标路径已存在，则跳过操作，并将文件状态记为`CONFLICT`。
*   **状态管理与可靠性:**
    *   使用SQLite数据库跟踪每个文件的状态 (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CONFLICT`)。
    *   所有外部API调用（LLM, TMDB）都必须有**重试机制**。
    *   对TMDB的API调用必须有**速率限制**。
    *   对LLM的调用必须有**缓存机制**。
    *   **异步安全:** 对同步的TMDB库调用必须用`asyncio.to_thread`包装。
    *   **并发安全:** 通过`asyncio.Queue`实现任务的原子分发，确保单个任务只被一个工作者处理。
*   **用户交互:** 通过`docker logs`查看由`loguru`生成的结构化日志。

#### **3. 系统架构与数据流 (The "How")**

采用解耦的**API层**和**核心逻辑服务**架构，两者通过共享的`asyncio.Queue`进行异步通信。

1.  **核心逻辑服务 (Core Logic Service):** 由**扫描器 (Scanner)** 和多个**处理器 (Processor)** 组成。
    *   **扫描器:** 作为独立的后台任务，发现新文件后，将文件ID作为任务推送到内存队列中。
    *   **处理器:** 多个并行的工作者 (Worker) 协程，以原子方式从队列中消费任务ID，并编排"识别->匹配->链接"的完整流程。
2.  **API层 (Backend API):** FastAPI应用，负责管理后台任务（扫描器和工作者）的生命周期，并为未来扩展UI做准备。

---

### **开发实践与技术栈 (The "Tools")**

#### **1. 项目结构 (Monorepo)**

```
/ClearMedia
├── .git/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── scanner.py
│   │   │   ├── processor.py
│   │   │   ├── llm.py
│   │   │   ├── tmdb.py
│   │   │   └── linker.py
│   │   ├── tests/             # ★ 新增测试目录
│   │   ├── config.py
│   │   ├── db.py
│   │   └── models.py
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt        # ★ 依赖锁定文件
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

#### **2. 技术栈**

| 类别 | 技术选型 |
| :--- | :--- |
| **后端语言** | **Python 3.11+** |
| **后端框架** | **FastAPI** |
| **配置管理** | **`pydantic-settings`** |
| **数据库 ORM** | **SQLite + SQLModel** |
| **API 交互** | **`openai`, `tmdbsimple`** |
| **可靠性** | **`tenacity` (重试), `asyncio.Semaphore` (限速), `async-lru` (缓存), `asyncio.to_thread` (异步包装)** |
| **日志** | **`loguru`** |
| **部署** | **Docker + Docker Compose** |
| **环境/包管理** | **`uv`** |
| **代码质量** | **`Ruff`**, `pre-commit` |

---

### **可执行的开发计划 (The "Action Plan")**

#### **Phase 1: 项目初始化与环境设置**

1.  **初始化项目:**
    *   创建项目根目录 `ClearMedia` 并 `git init`。
    *   创建 `backend` 目录，进入后执行 `uv init`。
2.  **安装依赖:**
    *   **运行时依赖:** `uv add fastapi "uvicorn[standard]" sqlmodel openai tmdbsimple python-dotenv pydantic-settings tenacity loguru`
    *   **开发时依赖:** `uv add --dev ruff pre-commit`
3.  **依赖锁定:**
    *   `uv export --format requirements-txt --no-hashes --group dev -o requirements-dev.txt`。
    *   `uv export --format requirements-txt --no-hashes  --no-dev  -o requirements.txt`
    *   **将 `backend/requirements.txt` 提交到Git仓库。**
4.  **设置预提交钩子 (可选但强烈推荐):**
    *   `pre-commit install`
    *   在项目根目录创建 `.pre-commit-config.yaml` 文件，并配置 `ruff`。
5.  **配置 `.gitignore`:** 在项目根目录创建，并忽略 `.venv/`, `__pycache__/`, `*.db`, `*.db-journal*`, `.pytest_cache/`。
6.  **创建 `.env.example`:** 列出所有需要的环境变量。

#### **Phase 2: 配置、数据库与核心模型**

1.  **`backend/app/config.py`:** 创建`Settings`类，继承自`pydantic_settings.BaseSettings`。
2.  **`backend/app/core/models.py`:** 实现 `MediaFile` SQLModel 模型，确保`status`字段的枚举值包含`CONFLICT`。
3.  **`backend/app/db.py`:** 实现 `get_db()` 依赖项函数。

#### **Phase 3: 核心业务逻辑 **

1.  **`backend/app/core/tmdb.py`:**
    *   在模块级别创建 `TMDB_SEMAPHORE = asyncio.Semaphore(10)`。
    *   所有调用`tmdbsimple`库函数的地方，都必须用 **`await asyncio.to_thread(...)`** 来包装。
    *   包装后的异步函数必须用 `@tenacity.retry(...)` 装饰。
2.  **`backend/app/core/llm.py`:**
    *   创建与LLM交互的函数，此函数必须用 `async-lru` 和 `@tenacity.retry(...)` 装饰。
3.  **`backend/app/core/linker.py`:**
    *   创建硬链接的函数。**在执行`os.link`前，必须先用`os.path.exists`检查目标路径。** 如果存在，则直接返回一个表示冲突的特定结果。
4.  **`backend/app/core/processor.py` 和 `scanner.py`:**
    *   `scanner`任务只负责发现新文件并将文件ID推入`asyncio.Queue`。
    *   `processor`函数从队列中获取ID，然后依次调用`llm`, `tmdb`, `linker`中的函数来完成整个流程，并根据每一步的结果更新数据库状态。

#### **Phase 4: API层与应用启动**

1.  **`backend/app/main.py`:**
    *   **配置Loguru:** 设置日志级别和格式。
    *   使用FastAPI的`lifespan`上下文管理器，在应用启动时，通过`asyncio.create_task()`启动`scanner`和多个`processor`工作者协程，并管理其生命周期。

#### **Phase 5: Docker化与部署 **

1.  **`backend/Dockerfile`:**
    *   **第一阶段 (builder):** `COPY pyproject.toml .`, `uv pip sync --system`。
    *   **第二阶段 (final):**
        *   `COPY backend/requirements.txt .`
        *   `pip install --no-cache-dir -r requirements.txt`
        *   `COPY app ./app`, 使用非root用户运行。
2.  **`docker-compose.yml`:** 保持不变，定义`backend`服务，映射卷和环境变量。

#### **Phase 6: 测试与迭代**

1.  在本地运行 `cp .env.example .env` 并填写你的配置。
2.  运行 `docker-compose up --build`。
3.  通过 `docker logs ClearMedia-backend-1 -f` 实时监控日志。
4.  **重点测试场景:**
    *   TMDB API瞬时不可用（验证重试）。
    *   并发处理大量文件（验证速率限制和多工作者处理）。
    *   目标文件已存在（验证冲突处理）。
    *   跨磁盘分区的硬链接（验证错误处理）。
5.  坚持使用**约定式提交**规范编写Git Commit。




### **模块开发指南 (细化版)**

#### **1. 模块: `linker.py` (文件链接器)**

*   **单一职责 (Purpose):**
    此模块封装了所有与**文件系统操作**相关的逻辑。它的核心任务是根据给定的源文件路径和计算出的目标文件路径，安全地创建一个硬链接。

*   **核心函数: `create_hardlink`**
    *   **输入参数:**
        1.  `source_path` (类型: `pathlib.Path`): 源文件的绝对路径。
        2.  `destination_path` (类型: `pathlib.Path`): 期望创建硬链接的目标绝对路径。
    *   **输出/返回:**
        返回一个表示操作结果的枚举或字符串常量。可能的结果包括：
        *   `LINK_SUCCESS`: 成功创建硬链接。
        *   `LINK_FAILED_CONFLICT`: 因目标路径已存在同名文件或目录而失败。
        *   `LINK_FAILED_CROSS_DEVICE`: 因源和目标不在同一文件系统而创建失败。
        *   `LINK_FAILED_NO_SOURCE`: 源文件不存在。
        *   `LINK_FAILED_UNKNOWN`: 其他未知`OSError`。
    *   **关键实现要点 (逻辑步骤):**
        1.  **前置检查 - 源文件:** 必须首先验证 `source_path` 是否存在并且是一个文件。如果不是，立即返回 `LINK_FAILED_NO_SOURCE`。
        2.  **前置检查 - 目标冲突:** 必须使用 `destination_path.exists()` 来检查目标路径是否**已经存在**。如果存在，立即返回 `LINK_FAILED_CONFLICT`，不进行任何操作。
        3.  **创建目标目录:** 在创建链接之前，必须确保目标文件的父目录存在。使用 `destination_path.parent.mkdir(parents=True, exist_ok=True)` 来递归创建目录结构。
        4.  **执行链接操作:** 将 `os.link(source_path, destination_path)` 调用包裹在一个 `try...except OSError` 块中。
        5.  **错误处理:** 在 `except` 块中，检查捕获到的`OSError`的`errno`属性。
            *   如果 `errno` 是 `errno.EXDEV` (跨设备链接错误)，则返回 `LINK_FAILED_CROSS_DEVICE`。
            *   对于所有其他`OSError`，记录详细的错误日志，并返回 `LINK_FAILED_UNKNOWN`。
        6.  **成功返回:** 如果`try`块成功执行，返回 `LINK_SUCCESS`。
    *   **依赖的第三方库:** 无，仅使用Python标准库 (`os`, `pathlib`, `errno`)。

---

#### **2. 模块: `processor.py` & `scanner.py` (工作流编排)**

##### **`scanner.py`**
*   **单一职责 (Purpose):**
    作为后台任务，持续扫描文件系统，发现新文件，并将它们作为"原材料"（文件ID）推送到内存任务队列中。它**不负责**任何处理逻辑。
*   **核心任务: `background_scanner_task`** (一个长时间运行的异步函数)
    *   **输入:** `media_queue: asyncio.Queue`。
    *   **输出:** 无（副作用是向数据库写入新记录，并向队列中推送文件ID）。
    *   **逻辑循环:**
        1.  在一个无限循环 (`while True`) 中执行。
        2.  遍历源目录下的所有文件。
        3.  对每个文件，获取其 `inode` 和 `device_id`。
        4.  查询数据库，检查该 `inode` + `device_id` 组合是否已存在。
        5.  如果**不存在**，则创建一个新的`MediaFile`对象（状态为`PENDING`），存入数据库后，将其**新生成的ID**推送到`media_queue`中。
        6.  循环结束后，调用`asyncio.sleep()`等待一个可配置的时间间隔，然后开始下一轮扫描。

##### **`processor.py`**
*   **单一职责 (Purpose):**
    作为整个应用的核心处理引擎函数。它接收一个任务ID，并按顺序调用其他模块（`llm`, `tmdb`, `linker`）来完成对一个文件的完整处理流程。它本身不包含循环或任务获取逻辑。
*   **核心函数: `process_media_file`** (一个可独立调用的异步函数)
    *   **输入:** `media_file_id: int`, 数据库会话工厂, 配置对象。
    *   **输出:** `ProcessResult`对象，包含处理结果（副作用是更新数据库中任务的状态和结果）。
    *   **逻辑步骤:**
        1.  在一个大的 `try...except...finally` 块中执行所有步骤。
        2.  **初始状态更新:** 获取任务后，立即在数据库中将其状态更新为 `PROCESSING`。
        3.  **步骤1: LLM分析。** 调用 `llm.analyze_filename()`。
        4.  **步骤2: TMDB搜索。** 使用上一步的结果，调用 `tmdb.search_media()`。
        5.  **步骤3: 生成新路径。** 根据TMDB的结果，计算出标准化的目标文件路径。
        6.  **步骤4: 创建链接。** 调用 `linker.create_hardlink()`。
        7.  **最终状态更新:** 在`finally`块中，根据处理是否成功，将任务状态更新为 `COMPLETED` 或 `FAILED`。如果链接时发生路径冲突，则特殊处理为 `CONFLICT` 状态。


1.搜索看能不能混合搜索, 或者混合搜索兜底,  LLM猜测错了类型会失败  (待优化,后续重构LLM为智能体,考虑引进Langgraph)
3.猜测tv的季也是全靠llm,这个不稳 ,看看TMDB有没有搜索季数的?


2.失败了之后就跳过了不做处理了吗?  结合前端,api触发重试,查询无结果不算失败,但是前端可以列出来

4.增加动漫的单独分类,或者搜索tv的信息的时候把分类也扒下来, tv和movie都爬取 GENRES id 作为分类标准,加到目标目录后面  没必要,取消

5.这个prompt, 如果有前端页面可以开放编辑,现在就先优化当前的prompt,提高准确率,也可以开发那个示例