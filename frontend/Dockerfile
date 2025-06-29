# 第一阶段：构建阶段
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 启用 corepack 以使用 pnpm
RUN corepack enable

# 复制 workspace 相关文件
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# 复制 frontend package.json
COPY frontend/package.json ./frontend/

# 安装依赖（使用 frozen-lockfile 确保一致性）
RUN pnpm install --frozen-lockfile

# 复制 frontend 源代码
COPY frontend/ ./frontend/

# 构建应用
RUN pnpm --filter frontend build

# 第二阶段：生产镜像
FROM nginx:1.27-alpine

# 复制 nginx 配置
COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"] 