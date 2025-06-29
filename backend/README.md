# ClearMedia 后端

本文档为 ClearMedia 的后端服务提供了一份全面的指南。该后端服务基于 FastAPI 构建，是一个用于扫描、处理和组织媒体文件的强大工具。

## 核心功能

-   **自动化媒体扫描**: 定期扫描源目录以发现新的媒体文件。
-   **丰富的元数据增强**: 从 TMDB 获取元数据，并使用 LLM 进行高级分析。
-   **智能文件整理**: 将文件重命名并整理到干净、结构化的目标目录中。
-   **动态配置**: 允许通过 REST API 进行实时配置更新，无需重启服务。
-   **强大的 API**: 提供用于查询文件、查看统计、重试失败任务和管理设置的端点。

## 架构概览

后端采用模块化和可扩展的架构设计，围绕一个健壮的媒体处理管线构建。

### 媒体处理工作流

处理服务由几个协同工作的专门模块组成：

```
backend/app/services/media/
├── scanner.py        # 扫描源目录以发现新文件
├── producer.py       # 将新文件添加到处理队列
├── processor.py      # 编排主要处理逻辑
├── status_manager.py # 管理每个媒体文件的状态
├── path_generator.py # 为文件生成最终目标路径
└── types.py          # 定义共享的数据结构
```

**工作流步骤:**

1.  **扫描 (Scanning)**: `scanner` 模块识别 `media_source` 目录中的新文件。
2.  **入队 (Queuing)**: `producer` 模块将发现的文件以 `PENDING` (待处理) 状态添加到数据库。
3.  **处理 (Processing)**: `processor` 模块获取待处理的文件并执行核心逻辑：
    -   从 **TMDB** 获取元数据。
    -   (可选) 使用 **LLM** 进行更深入的分析。
    -   使用 `path_generator` 生成一个新的、干净的文件名和路径。
    -   在 `media_target` 目录中创建一个符号链接。
4.  **状态更新**: `status_manager` 确保在每一步都原子地更新文件的状态 (`PROCESSING`, `COMPLETED`, `FAILED` 等)。

### 设计优势

-   **单一职责**: 每个模块都有明确定义的用途，简化了维护和测试。
-   **逻辑解耦**: 基于队列的方法将文件发现与处理解耦，提高了系统的弹性。
-   **可测试性**: 独立的模块易于进行单元测试。

## API 文档

API 提供了对媒体库和系统配置的完全控制。

> **基础 URL**: `http://<host>:8000/api`
> **交互式文档**:
> - **Swagger UI**: `http://<host>:8000/docs`
> - **ReDoc**: `http://<host>:8000/redoc`

---

### 媒体端点 (`/files`)

#### `GET /api/files`

获取媒体文件的分页列表，支持筛选、搜索和排序。

| 参数 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `skip` | `int` | `0` | 分页偏移量。 |
| `limit` | `int` | `20` | 返回的项目数 (1-500)。 |
| `status` | `string` | (可选) | 按状态筛选 (例如, `COMPLETED`, `FAILED`)。支持多个值，用逗号分隔。 |
| `search` | `string` | (可选) | 按文件名进行关键字搜索。 |
| `sort` | `string` | `created_at:desc` | 排序顺序 (例如, `updated_at:asc`)。 |

#### `GET /api/files/{file_id}`

按 ID 获取单个媒体文件的详细信息。

#### `POST /api/files/{file_id}/retry`

重试处于 `FAILED`、`NO_MATCH` 或 `CONFLICT` 状态的文件，方法是将其状态重置为 `PENDING`。

#### `POST /api/files/batch-retry`

批量重试一组文件。

-   **请求体**: `{ "file_ids": [1, 2, 3] }`

#### `POST /api/files/batch-delete`

批量删除文件的数据库记录 (不会删除磁盘上的实际文件)。

-   **请求体**: `{ "file_ids": [1, 2, 3] }`

#### `GET /api/files/suggest`

根据关键字为自动完成功能提供文件名建议。

---

### 统计端点 (`/stats`)

#### `GET /api/stats`

返回按状态分组的媒体文件摘要 (例如, `{ "COMPLETED": 120, "FAILED": 5 }`)。

---

### 配置端点 (`/config`)

#### `GET /api/config`

获取当前系统配置。敏感密钥 (如 API 密钥) 会被隐去。

#### `POST /api/config`

更新一个或多个配置值并触发热重载。只有非黑名单中的密钥可以被修改。

-   **请求体**: `{ "LOG_LEVEL": "INFO", "TMDB_CONCURRENCY": 8 }`

## 本地开发

1.  **安装依赖**:
    ```bash
    # 确保您位于项目根目录
    pnpm install
    ```

2.  **运行服务**:
    使用 `uv` 运行开发服务器，它支持热重载并能读取 `.env` 文件。
    ```bash
    uv run uvicorn main:app --app-dir backend --reload --port 8000
    ```