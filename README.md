# ClearMedia 项目概览

ClearMedia 是一个用于多格式媒体扫描、转码及组织的全栈应用，后端基于 **FastAPI**，前端基于 **React 19 + Vite**。

## 目录结构

```
.
├── backend/   # FastAPI 后端服务
├── frontend/  # React 前端 SPA
└── docker-compose.yml
```

## 快速启动

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

## Husky & lint-staged

项目使用 **Husky** 在 Git 提交阶段运行 `lint-staged`，自动格式化并检测待提交文件，减少 CI 失败概率。首次 `pnpm install` 后自动执行 `pnpm prepare` 安装提交钩子。

