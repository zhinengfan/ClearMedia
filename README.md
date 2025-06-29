# ClearMedia 项目概览

ClearMedia 是一个用于多格式媒体扫描、转码及组织的全栈应用，后端基于 **FastAPI**，前端基于 **React 19 + Vite**。

## 目录结构

```
.
├── backend/   # FastAPI 后端服务
├── frontend/  # React 前端 SPA
└── docker-compose.yml
```

## 一键部署（推荐）

使用 Docker Compose 可以一键启动完整的应用栈：

```bash
# 构建并启动所有服务
docker compose build --parallel
docker compose up -d

# 访问应用
# 前端：http://localhost
# 后端 API：http://localhost/api
# 后端直接访问：http://localhost:8000
```

### 服务说明

| 服务 | 容器名 | 端口映射 | 说明 |
|------|--------|----------|------|
| frontend | clearmedia-frontend | 80:80 | Nginx 托管的前端 SPA，包含 /api 反向代理 |
| backend | clearmedia-backend | 8000:8000 | FastAPI 后端服务 |


### 停止服务

```bash
docker compose down
```

## 开发模式

> 以下命令均在 **项目根目录** 执行，假设已安装 [pnpm](https://pnpm.io/) 与 [uv](https://github.com/astral-sh/uv). 如无 uv，请替换为 `python -m uvicorn` 等等。

1. 安装依赖（包含前后端）

   ```bash
   pnpm install
   ```

2. 启动后端（使用 [uv](https://github.com/astral-sh/uv) 以确保 .env 能被正确读取）

   ```bash
   uv run uvicorn main:app --app-dir backend --reload --port 8000
   ```

3. 启动前端

   ```bash
   pnpm dev   # 等价于 pnpm --filter frontend dev
   ```

4. 访问应用

   - 后端 API: http://localhost:8000/api
   - 前端 SPA: http://localhost:5173

## 常用脚本

| 脚本                 | 位置          | 功能说明                           |
| -------------------- | ------------- | ---------------------------------- |
| `pnpm dev`           | 根            | 同时方便开启前端开发服务器         |
| `pnpm build`         | 根            | 构建前端产物（位于 `frontend/dist/`） |
| `pnpm preview`       | 根            | 本地预览生产构建结果               |
| `pnpm lint`          | frontend      | ESLint 检查                        |
| `pnpm format`        | frontend      | Prettier 格式化                    |
| `pnpm prepare`       | frontend      | 初始化 Husky Git 钩子              |

## 环境变量

项目根目录的 `.env` 文件包含后端配置,参考`.env.example`：

```bash
# 示例配置
DATABASE_URL=sqlite:///./clearmedia.db
MEDIA_SOURCE_PATH=/data/source
MEDIA_TARGET_PATH=/data/target
```

容器化部署时，这些路径会自动映射到容器内的对应目录。

## Husky & lint-staged

项目使用 **Husky** 在 Git 提交阶段运行 `lint-staged`，自动格式化并检测待提交文件，减少 CI 失败概率。首次 `pnpm install` 后自动执行 `pnpm prepare` 安装提交钩子。

