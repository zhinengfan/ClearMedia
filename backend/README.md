# ClearMedia 后端服务

这是 ClearMedia 项目的后端服务。

## Docker 部署指南

本指南将说明如何使用 Docker 和 Docker Compose 部署后端服务。

### 前提条件

1.  **Docker 与 Docker Compose**: 请确保您的系统中已安装这两个工具。
2.  **环境变量**: 复制环境变量示例文件，并根据您的环境进行配置。

    ```bash
    # 首先，复制 .env.example 文件为 .env
    cp .env.example .env
    # 然后，编辑 .env 文件，填入您的特定配置。
    # 请特别注意媒体库路径和 API 密钥等设置。
    ```

### 运行服务

1.  **构建 Docker 镜像**

    使用 Docker Compose 构建服务镜像。请在项目根目录下执行此命令。

    ```bash
    docker compose build
    ```

2.  **启动容器**

    以分离模式 (`-d`) 运行容器。

    ```bash
    docker compose up -d
    ```

3.  **检查状态**

    您可以使用以下命令验证容器是否正在运行：

    ```bash
    docker compose ps
    ```

### 查看日志

要查看后端服务的实时日志：

```bash
docker compose logs -f
```

### 常见问题 (FAQ)

-   **端口 8000 已被占用**:
    如果您看到关于端口 8000 被占用的错误消息，说明您机器上的另一个服务正在使用它。您可以停止该服务，或者在 `docker-compose.yml` 文件中更改端口映射。例如，将 `"8000:8000"` 修改为 `"8001:8000"`，以将其映射到主机的 8001 端口。

-   **挂载卷权限不足**:
    如果容器无法读取或写入 `media_source` 或 `media_target` 目录，这很可能是宿主机上的文件权限问题。请确保运行 Docker 容器的用户拥有必要的权限。在 Linux 系统上，您可能需要使用 `chown` 或 `chmod` 命令来调整目录所有权或权限。

### API 使用说明

> 所有接口默认根路径为 `http://<host>:8000/api`。
> 在容器环境中可将 `<host>` 替换为宿主机地址或 `localhost`（端口可能已映射）。

#### 1. GET `/files`
查询媒体文件列表，支持分页、状态过滤、文件名模糊搜索与排序。

| 参数         | 类型                                   | 默认值            | 说明                                                                                                  |
|--------------|----------------------------------------|-------------------|-------------------------------------------------------------------------------------------------------|
| `skip`       | int (>=0)                              | `0`               | 跳过的记录数（分页起始偏移量）                                                                         |
| `limit`      | int (1~500)                            | `20`              | 返回记录数限制                                                                                        |
| `status`     | string                                 | *(可选)*          | 按状态筛选，可选值: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `CONFLICT`, `NO_MATCH`            |
| `search`     | string                                 | *(可选)*          | 文件名模糊搜索关键字                                                                                  |
| `sort`       | enum                                   | `created_at:desc` | 排序方式，可选 `created_at:asc` 或 `created_at:desc`                                                  |

**示例**
```bash
curl -G 'http://localhost:8000/api/files' \
     --data-urlencode 'limit=50' \
     --data-urlencode 'status=COMPLETED' \
     --data-urlencode 'sort=created_at:asc'
```

---

#### 2. GET `/files/suggest`
根据文件名前缀提供自动补全建议。

| 参数     | 类型            | 默认值   | 说明                                      |
|----------|-----------------|----------|-------------------------------------------|
| `keyword`| string (必填)   | —        | 文件名前缀关键字                          |
| `limit`  | int (1~100)     | `20`     | 返回建议数量限制                          |

**示例**
```bash
curl -G 'http://localhost:8000/api/files/suggest' --data-urlencode 'keyword=movie'
```

---

#### 3. GET `/files/{file_id}`
根据文件 ID 获取媒体文件详情。

**示例**
```bash
curl 'http://localhost:8000/api/files/123'
```

---

#### 4. GET `/stats`
获取按状态分组的媒体文件数量统计。

**示例**
```bash
curl 'http://localhost:8000/api/stats'
```

---

#### 5. POST `/files/{file_id}/retry`
对 `FAILED` / `NO_MATCH` / `CONFLICT` 状态的媒体文件重新排队处理。

**示例**
```bash
curl -X POST 'http://localhost:8000/api/files/123/retry'
```

> 若重试成功，接口将返回当前状态已更新为 `PENDING` 的确认信息。

---

### 查看 Swagger UI / ReDoc

构建并运行容器后，打开以下地址获取 OpenAPI 文档：

- Swagger UI: `http://<host>:8000/docs`
- ReDoc: `http://<host>:8000/redoc`

如文档与实际接口不一致，请先检查依赖任务是否已合并并重新构建镜像。
