# ClearMedia 前端

本文档涵盖了 ClearMedia 前端的设置、架构和开发流程。这是一个使用 **React 19、TypeScript 和 Vite** 构建的现代化 Web 应用。

## 核心功能

-   **仪表盘**: 媒体处理统计和近期活动的概览。
-   **文件管理**: 一个综合表格，用于查看、搜索、筛选和排序所有媒体文件。
-   **详情视图**: 一个可滑出的面板，用于检查任何单个文件的详细信息。
-   **批量操作**: 一次性重试或管理多个失败的文件。
-   **动态设置**: 一个用户友好的界面，用于实时查看和更新后端配置。

## 技术栈

-   **框架**: React 19
-   **语言**: TypeScript
-   **构建工具**: Vite
-   **样式**: Tailwind CSS & shadcn/ui
-   **路由**: TanStack Router
-   **数据获取**: 使用 `fetch` 的自定义 Hooks
-   **代码质量**: ESLint, Prettier, 和 Husky

## 目录结构

`src` 目录按功能和职责进行组织：

```
frontend/src/
├── components/   # 可复用 UI 组件 (例如, DataTable, Sidebar)
├── hooks/        # 自定义 Hooks (例如, useConfig, useDebounce)
├── lib/          # 核心工具 (例如, api.ts, toast.ts)
├── pages/        # 顶层页面组件 (Dashboard, Files, Settings)
├── router.tsx    # 应用路由配置
└── main.tsx      # 应用主入口点
```

## 本地开发

### 先决条件

-   Node.js >= 20
-   pnpm >= 10

### 设置

1.  **安装依赖**:
    在项目根目录运行：
    ```bash
    pnpm install
    ```

2.  **配置环境**:
    Vite 开发服务器已配置为将所有从 `/api` 发出的请求代理到运行在 `http://localhost:8000` 的后端服务器。此配置在 `vite.config.ts` 中处理，无需额外的环境配置。

3.  **运行服务**:
    您需要同时运行后端和前端服务器。

    -   **启动后端**:
        在一个终端中，从项目根目录运行：
        ```bash
        uv run uvicorn main:app --app-dir backend --reload --port 8000
        ```

    -   **启动前端**:
        在另一个终端中，从项目根目录运行：
        ```bash
        pnpm -F frontend dev
        ```

    前端应用将在 `http://localhost:5173` 上可用。

## 代码质量

项目配备了工具来保持高代码质量。

-   `pnpm lint`: 运行 ESLint 检查代码问题。
-   `pnpm format`: 使用 Prettier 格式化所有文件。
-   **Husky Git Hooks**: 在每次提交之前，`lint-staged` 会自动格式化并检查暂存文件。