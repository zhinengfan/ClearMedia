### **项目蓝图：ClearMedia (v1.5 更新)**

#### **1. 项目概述 (The "Why")**

*   **项目名称:** ClearMedia
*   **目标:** 开发一款智能媒体整理工具，利用LLM对不规范的媒体文件名进行识别，从TMDB获取准确元数据，并将其重命名/链接为媒体服务器的标准格式。
*   **演进:** 项目已从纯后端服务演进为一个功能完备的**API驱动型应用**，提供丰富的REST API，为前端Web UI集成做好了充分准备。
*   **服务对象:** 拥有NAS并熟悉Docker环境的家庭用户。
*   **核心价值:** 高识别率、自动化、非侵入式（支持硬链接保种）、易于部署和交互。

#### **2. 功能范围 (The "What")**

*   **配置:** 通过项目根目录的`.env`文件进行配置。
*   **扫描:** 定时扫描用户指定的"源文件夹" (`SOURCE_DIR`)。
*   **文件标识:** 使用文件的`inode` + `device_id`作为唯一标识，避免重复处理。
*   **识别流程:**
    1.  对新文件，调用**LLM**进行智能分析，提取`标题`、`年份`和`类型`，并强制以JSON格式返回。
    2.  使用从LLM获取的信息，查询**TMDB API**以获得精确的官方媒体数据。
    3.  **混合搜索:** 当LLM猜测的媒体类型（如`movie`）搜索无果时，会自动尝试其他类型（如`tv`），提高识别成功率。
*   **文件操作:**
    *   **仅支持硬链接 (`hardlink`) 模式**。
    *   **冲突处理:** 若目标路径已存在，则跳过操作，并将文件状态记为`CONFLICT`。
*   **状态管理与可靠性:**
    *   使用SQLite数据库跟踪每个文件的状态 (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CONFLICT`, `NO_MATCH`)。
    *   **`NO_MATCH` 状态:** 当TMDB搜索确认无匹配结果时，将文件标记为此状态，以便从失败状态中区分开，方便后续手动处理。
    *   所有外部API调用（LLM, TMDB）都必须有**重试机制**。
    *   对TMDB的API调用必须有**速率限制**。
    *   对LLM的调用必须有**缓存机制**。
    *   **异步安全:** 对同步的TMDB库调用必须用`asyncio.to_thread`包装。
    *   **并发安全:** 通过`asyncio.Queue`实现任务的原子分发，确保单个任务只被一个工作者处理。
*   **用户交互:** 
    *   **API:** 提供了一套完整的REST API，用于查询、统计、手动重试文件。
    *   **日志:** 通过`docker logs`查看由`loguru`生成的结构化日志。

#### **3. 系统架构与数据流 (The "How")**

采用解耦的**API层**和**核心逻辑服务**架构，两者通过共享的`asyncio.Queue`进行异步通信。

1.  **核心逻辑服务 (Core Logic Service):** 由**扫描器 (Scanner)** 和多个**处理器 (Processor)** 组成。
    *   **扫描器:** 作为独立的后台任务，发现新文件后，将文件ID作为任务推送到内存队列中。
    *   **处理器:** 多个并行的工作者 (Worker) 协程，以原子方式从队列中消费任务ID，并编排"识别->匹配->链接"的完整流程。
2.  **API层 (Backend API):** FastAPI应用，不仅负责管理后台任务的生命周期，还提供了一系列丰富的REST API端点，用于与前端UI或外部工具交互，实现对媒体库状态的全面监控和管理。

---

### **开发实践与技术栈 (The "Tools")**

#### **1. 项目结构 (Monorepo)**

```
/ClearMedia
├── .git/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/              # ★ API包：聚合器与 endpoints
│   │   │   ├── __init__.py   #   聚合器 router + OpenAPI 标签
│   │   │   └── endpoints/
│   │   │       ├── media.py  #   媒体相关路由
│   │   │       └── config.py #   配置管理路由
│   │   ├── crud.py            # ★ 数据库增删改查
│   │   ├── db.py
│   │   ├── processor.py       # ★ 核心处理逻辑
│   │   ├── scanner.py         # ★ 文件扫描逻辑
│   │   ├── config.py
│   │   ├── core/              # ★ 核心工具/模型
│   │   │   ├── __init__.py
│   │   │   ├── llm.py
│   │   │   ├── tmdb.py
│   │   │   ├── linker.py
│   │   │   └── models.py
│   │   └── tests/
│   ├── main.py                # ★ FastAPI应用入口
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

#### **2. 技术栈**

| 类别 | 技术选型 |
| :--- | :--- |
| **后端语言** | **Python 3.12+** |
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
    *   并发处理大量文件（验证速率限制和多工作者处理）。
    *   目标文件已存在（验证冲突处理）。
    *   跨磁盘分区的硬链接（验证错误处理）。
5.  坚持使用**约定式提交**规范编写Git Commit。


### **当前状态与待办事项**

#### **已实现的关键功能**
- **[已完成] 混合搜索:** `tmdb.py` 中已实现，当LLM猜测的类型搜索失败时，会自动尝试另一种媒体类型（Movie/TV），显著提高了识别率。
- **[已完成] 手动重试机制:** 已通过 `POST /api/files/{file_id}/retry` API 端点实现。对于`FAILED`, `NO_MATCH`, `CONFLICT`状态的文件，可以触发一次重新处理。
- **[已完成] `NO_MATCH` 状态:** `processor.py` 中已引入此新状态，用于明确标识那些"已尝试处理，但TMDB中无匹配项"的文件，将其与因网络或API错误导致的`FAILED`状态区分开。
- **[已完成] 健壮的LLM交互:** `llm.py` 中实现了详细的系统Prompt和可靠的JSON解析逻辑，能处理LLM返回的多余字符。
- **[已完成] 完整功能的API:** 新的 `app.api` 包提供文件查询、统计、详情、手动重试及 **配置管理 (GET/POST /api/config)** 等完整REST接口，为前端集成提供全面支持。

#### **待优化与未来方向**
- **[待优化] TV剧季信息识别:** 当前`season`的识别完全依赖LLM，准确性有待提高。未来可研究TMDB API是否支持更精确的季、集搜索方式。
- **[待探索] 引入LangGraph:** 考虑将当前的LLM调用重构为更强大的智能体，利用LangGraph或类似框架管理更复杂的判断逻辑和工具调用链。
- **[待优化] Prompt优化:** 虽然当前Prompt已很详细，但仍有优化空间。可以考虑在前端提供界面，让用户可以自定义或提供Few-shot示例来动态调整Prompt。

---

### **模块开发指南 (细化版)**

#### **1. 模块: `linker.py` (文件链接器)**

*   **单一职责 (Purpose):**
    此模块封装了所有与**文件系统操作**相关的逻辑。它的核心任务是根据给定的源文件路径和计算出的目标文件路径，安全地创建一个硬链接。

*   **核心函数: `create_hardlink`**
    *   **输入参数:**
        1.  `source_path` (类型: `pathlib.Path`): 源文件的绝对路径。
        2.  `destination_path` (类型: `pathlib.Path`): 期望创建硬链接的目标绝对路径。
    *   **输出/返回:**
        返回一个 `LinkResult` 枚举，表示操作结果 (`LINK_SUCCESS`, `LINK_FAILED_CONFLICT`, `LINK_FAILED_CROSS_DEVICE`, 等)。
    *   **实现状态:** **已完成**，功能与规范完全一致。
    *   **关键实现要点 (逻辑步骤):**
        1.  **前置检查 - 源文件:** 验证 `source_path` 是否存在且为文件。
        2.  **前置检查 - 目标冲突:** 使用 `destination_path.exists()` 检查目标路径是否**已经存在**。
        3.  **创建目标目录:** 使用 `destination_path.parent.mkdir(parents=True, exist_ok=True)` 确保父目录存在。
        4.  **执行链接操作:** 将 `os.link(...)` 包裹在 `try...except OSError` 块中。
        5.  **错误处理:** 在 `except` 块中检查`OSError`的`errno`属性，以区分跨设备链接等不同错误。
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
    *   **实现状态:** **已完成**。
    *   **逻辑循环:**
        1.  在一个无限循环 (`while True`) 中执行，并可通过 `asyncio.Event` 优雅地停止。
        2.  遍历源目录下的所有文件，支持按扩展名、最小文件大小进行过滤，并可配置是否排除目标目录。
        3.  对每个文件，获取其 `inode` 和 `device_id`。
        4.  查询数据库，检查该 `inode` + `device_id` 组合是否已存在。
        5.  如果**不存在**，则创建一个新的`MediaFile`对象（状态为`PENDING`），存入数据库后，将其**新生成的ID**推送到`media_queue`中。
        6.  循环结束后，调用`asyncio.sleep()`等待一个可配置的时间间隔，然后开始下一轮扫描。

##### **`processor.py`**
*   **单一职责 (Purpose):**
    作为整个应用的核心处理引擎函数。它接收一个任务ID，并按顺序调用其他模块（`llm`, `tmdb`, `linker`）来完成对一个文件的完整处理流程。
*   **核心函数: `process_media_file`** (一个可独立调用的异步函数)
    *   **输入:** `media_file_id: int`, 数据库会话工厂, 配置对象。
    *   **输出:** `ProcessResult`对象（副作用是更新数据库中任务的状态和结果）。
    *   **实现状态:** **已完成**。
    *   **高级功能:**
        *   **混合搜索:** 当从LLM获取类型后，调用 `tmdb.search_media` 进行搜索。该函数内部实现了如果主类型搜索失败，自动尝试备用类型的逻辑。
        *   **状态细化:** 能正确处理 `CONFLICT` 和 `NO_MATCH` 状态。当TMDB搜索无果时，将状态置为 `NO_MATCH` 而非 `FAILED`。
    *   **逻辑步骤:**
        1.  在一个大的 `try...except...finally` 块中执行所有步骤。
        2.  **初始状态更新:** 获取任务后，立即在数据库中将其状态更新为 `PROCESSING`。
        3.  **步骤1: LLM分析。** 调用 `llm.analyze_filename()`，内置了缓存和重试。
        4.  **步骤2: TMDB搜索。** 调用 `tmdb.search_media()`，内置了混合搜索、缓存、重试和速率限制。
        5.  **步骤3: 生成新路径。** 根据TMDB的结果，计算出标准化的目标文件路径，支持电影和电视剧两种格式。
        6.  **步骤4: 创建链接。** 调用 `linker.create_hardlink()`，并根据返回结果处理成功、冲突或失败等情况。
        7.  **最终状态更新:** 在`finally`块中，根据处理是否成功，将任务状态更新为 `COMPLETED` 或 `FAILED`。如果链接时发生路径冲突或TMDB无匹配，则特殊处理为 `CONFLICT` 或 `NO_MATCH` 状态。