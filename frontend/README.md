# ClearMedia 前端开发指南

本仓库的 `frontend` 子项目基于 **React 19 + TypeScript + Vite** 搭建，使用 **Tailwind CSS 4** 进行样式开发。

> 项目使用 **pnpm** 作为包管理工具，并依赖 **Monorepo workspace**（根目录 `package.json` 的 `workspaces` 字段）。

## 环境要求

- Node.js ≥ 20.x
- pnpm ≥ 10.x（推荐通过 `corepack enable` 启用）
- Git（用于 Husky 提交钩子）

## 快速开始

1. **安装依赖**（在项目根目录执行，确保安装 workspace 依赖）

   ```bash
   pnpm install
   ```

2. **启动开发服务器**

   ```bash
   # 启动后端（另一个终端中执行）
   uv run uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000  --reload

   # 启动前端
   pnpm dev            # 等价于 pnpm --filter frontend dev
   ```

   前端将通过 Vite 启动，默认监听 `http://localhost:5173`。如需修改端口请参见 `vite.config.ts`。

3. **构建生产包**

   ```bash
   pnpm build          # 等价于 pnpm --filter frontend build
   ```

4. **预览生产包**

   ```bash
   pnpm preview        # 本地预览 dist
   ```

## 代码质量

本项目启用了 **ESLint**、**Prettier** 与 **Husky + lint-staged**，在提交前会自动执行格式化与 Lint 校验。

| 命令             | 说明                                  |
| ---------------- | ------------------------------------- |
| `pnpm lint`      | 运行 ESLint 检查                      |
| `pnpm lint:fix`  | 自动修复可修复的 Lint 问题            |
| `pnpm format`    | 使用 Prettier 对代码进行格式化        |
| `pnpm format:check` | 检查格式化（只读，不写入）           |
| `pnpm prepare`   | 初始化 Husky Git 钩子（install 时自动）|

> 安装依赖后将自动执行 `pnpm prepare` 并在 `.husky/` 目录写入 Git 钩子，需要保证本机 Git 已开启执行权限。

## 目录结构概览

```
frontend/
├── src/              # 业务源码
│   ├── components/   # 通用 UI 组件
│   ├── hooks/        # 通用 Hook
│   ├── pages/        # 路由页面
│   ├── router.tsx    # 路由配置（@tanstack/react-router）
│   └── main.tsx      # 入口文件
├── public/           # 公共静态资源
├── tailwind.config.ts
├── vite.config.ts
└── package.json
```

## 与后端联调

默认情况下，前端通过环境变量或在 `.env` 文件中配置的 `VITE_API_BASE_URL` 访问后端接口。

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000/api
```

在开发模式下，Vite 会自动将前缀为 `/api` 的请求代理到该后端地址，详见 `vite.config.ts` 中的 `proxy` 设置。


