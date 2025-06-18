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

#### **2. 模块: `queue.py` (原子任务队列)**

*   **单一职责 (Purpose):**
    此模块负责以**并发安全**的方式从数据库中获取待处理的任务。它确保在多进程/多线程环境下，同一个“待办”任务不会被多个工作者重复领取。

*   **核心函数: `acquire_next_task`**
    *   **输入参数:**
        1.  `db_session` (类型: `sqlmodel.Session`): 当前的数据库会话对象。
    *   **输出/返回:**
        *   如果成功获取并锁定了任务，返回该任务的 `MediaFile` ORM对象。
        *   如果没有可处理的任务，返回 `None`。
    *   **关键实现要点 (逻辑步骤):**
        1.  **原子性是关键:** 这个函数的所有数据库操作都必须在一个事务中完成。
        2.  **查询阶段:** 使用SQLAlchemy Core或SQLModel构建一个查询，目标是 `MediaFile` 表中 `status` 为 `PENDING` 的记录。
        3.  **锁定机制:**
            *   这是实现原子性的核心。在查询中必须加入**行级锁**机制。使用SQLAlchemy，这通过 `.with_for_update(skip_locked=True)` 方法实现。
            *   `FOR UPDATE` 会锁定查询到的行，防止其他事务修改它。
            *   `SKIP LOCKED` (适用于PostgreSQL等，SQLite不支持但理念相同) 告诉数据库如果行已经被其他事务锁定了，就直接跳过它，而不是等待锁释放。这可以防止多个工作者互相等待。
        4.  **获取第一个可用任务:** 在查询中加入 `.first()`，只获取一个未被锁定的`PENDING`任务。
        5.  **状态更新:** 如果成功获取到了一个任务（即 `task` 不为 `None`），**必须立即**在同一个事务内将其状态更新为 `PROCESSING` (`task.status = FileStatus.PROCESSING`)。
        6.  **提交事务:** 提交数据库会话 (`db_session.commit()`)，这将释放行锁并持久化状态变更。
        7.  **返回任务对象:** 将获取到的 `task` 对象返回给调用者。如果最初没有查询到任何任务，则直接返回`None`。
    *   **依赖的第三方库:** `sqlmodel` / `sqlalchemy`。

---

#### **3. 模块: `processor.py` & `scanner.py` (工作流编排)**

##### **`scanner.py`**
*   **单一职责 (Purpose):**
    作为后台任务，持续扫描文件系统，发现新文件，并将它们作为“原材料”添加到任务队列中。它**不负责**任何处理逻辑。
*   **核心任务: `background_scanner_task`** (一个长时间运行的异步函数)
    *   **输入:** 无（从`config.py`获取源目录路径）。
    *   **输出:** 无（副作用是向数据库中写入新记录）。
    *   **逻辑循环:**
        1.  在一个无限循环 (`while True`) 中执行。
        2.  遍历源目录下的所有文件。
        3.  对每个文件，获取其 `inode` 和 `device_id`。
        4.  查询数据库，检查该 `inode` + `device_id` 组合是否已存在。
        5.  如果**不存在**，则创建一个新的`MediaFile`对象，状态为`PENDING`，并将其添加到数据库中。
        6.  循环结束后，调用`asyncio.sleep()`等待一个可配置的时间间隔（例如300秒），然后开始下一轮扫描。

##### **`processor.py`**
*   **单一职责 (Purpose):**
    作为后台任务，是整个应用的核心处理引擎。它持续地从队列中获取任务，并按顺序调用其他模块（`llm`, `tmdb`, `linker`）来完成对一个文件的完整处理流程。
*   **核心任务: `background_processor_task`** (一个长时间运行的异步函数)
    *   **输入:** 无。
    *   **输出:** 无（副作用是更新数据库中任务的状态和结果）。
    *   **逻辑循环:**
        1.  在一个无限循环中执行。
        2.  调用 `queue.acquire_next_task()` 来**原子地获取**一个待处理的任务。
        3.  **如果获取到任务 (`task` is not `None`):**
            a.  在一个大的 `try...except` 块中执行以下所有步骤，以捕获任何意外失败。
            b.  **步骤1: LLM分析。** 调用 `llm.analyze_filename()`，传入`task.original_filename`。如果失败，记录错误，更新任务状态为`FAILED`，然后`continue`到下一次循环。
            c.  **步骤2: TMDB搜索。** 使用上一步的结果，调用 `tmdb.search_media()`。如果失败或未找到匹配项，记录错误，更新任务状态为`FAILED`，然后`continue`。
            d.  **步骤3: 生成新路径。** 根据TMDB的结果，计算出标准化的目标文件路径。
            e.  **步骤4: 创建链接。** 调用 `linker.create_hardlink()`，传入源路径和新计算出的目标路径。
            f.  **步骤5: 更新最终状态。** 根据`linker`返回的结果，将任务状态更新为 `COMPLETED` 或 `CONFLICT`。
        4.  **如果未获取到任务 (`task` is `None`):**
            *   调用`asyncio.sleep()`等待一个较短的时间（例如5秒），然后尝试再次获取任务。这可以避免在没有任务时空转CPU。