### **项目蓝图：ClearMedia **

#### **1. 项目概述 (The "Why")**

*   **项目名称:** ClearMedia
*   **目标:** 开发一款智能媒体整理工具，利用LLM对不规范的媒体文件名进行识别，从TMDB获取准确元数据，并将其重命名/链接为媒体服务器的标准格式。
*   **服务对象:** 拥有NAS并熟悉Docker环境的家庭用户。
*   **核心价值:** 高识别率、自动化、非侵入式（支持硬链接保种）、易于部署。

#### **2. 最小可行产品 (MVP) 范围 (The "What")**

MVP的核心是一个纯后端服务，无Web前端界面，通过Docker运行。

*   **配置:** 通过项目根目录的`.env`文件进行配置。
*   **扫描:** 定时扫描用户指定的“源文件夹” (`SOURCE_DIR`)。
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
    *   **并发安全:** 从数据库获取待处理任务必须是**原子操作**，防止多进程重复处理。
*   **用户交互:** 通过`docker logs`查看由`loguru`生成的结构化日志。

#### **3. 系统架构与数据流 (The "How")**

采用解耦的**API层**和**核心逻辑服务**架构，两者通过共享数据库进行异步通信。

1.  **核心逻辑服务 (Core Logic Service):** 独立的后台任务，持续运行，以**原子方式**从数据库获取待处理任务，并编排“识别->匹配->链接”的完整流程。
2.  **API层 (Backend API):** FastAPI应用，MVP阶段仅提供健康检查端点，为未来扩展UI做准备。

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
│   │   │   ├── queue.py        # ★ 负责原子地获取任务
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
| **可靠性** | **`tenacity` (重试), `asyncio.Semaphore` (限速), `functools.lru_cache` (缓存), `asyncio.to_thread` (异步包装)** |
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
    *   创建与LLM交互的函数，此函数必须用 `@functools.lru_cache(maxsize=128)` 和 `@tenacity.retry(...)` 装饰。
3.  **`backend/app/core/linker.py`:**
    *   创建硬链接的函数。**在执行`os.link`前，必须先用`os.path.exists`检查目标路径。** 如果存在，则直接返回一个表示冲突的特定结果。
4.  **`backend/app/core/queue.py`:**
    *   创建一个函数 `get_next_task_atomically(db: Session)`。
    *   此函数的核心是执行一个**原子操作**来获取并锁定下一个待处理任务，例如使用 `SELECT ... FOR UPDATE SKIP LOCKED` (具体实现取决于SQLAlchemy对SQLite的支持，或使用更直接的`UPDATE ... RETURNING`语句)。
5.  **`backend/app/core/processor.py` 和 `scanner.py`:**
    *   `scanner`任务只负责发现新文件并创建`PENDING`记录。
    *   `processor`任务的循环中，调用 `queue.py` 中的函数来安全地获取任务，然后依次调用`llm`, `tmdb`, `linker`中的函数来完成整个流程，并根据每一步的结果更新数据库状态。

#### **Phase 4: API层与应用启动**

1.  **`backend/app/main.py`:**
    *   **配置Loguru:** 设置日志级别和格式。
    *   使用 `@app.on_event("startup")` 装饰器，在应用启动时，使用 `asyncio.create_task()` 启动后台任务。

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
    *   并发处理大量文件（验证速率限制）。
    *   目标文件已存在（验证冲突处理）。
    *   跨磁盘分区的硬链接（验证错误处理）。
5.  坚持使用**约定式提交**规范编写Git Commit。