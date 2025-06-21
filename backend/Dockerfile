# 第一阶段：构建阶段，安装依赖
FROM python:3.12-slim AS builder

WORKDIR /app

# 复制依赖文件
COPY backend/requirements.txt ./

# 安装运行时依赖
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# 第二阶段：仅包含运行所需内容
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 复制依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 复制应用源码
COPY backend/app ./app
COPY backend/main.py .

# 创建非 root 用户
RUN adduser --disabled-password --gecos "" --uid 1000 clearmedia && \
    chown -R clearmedia:clearmedia /app

USER clearmedia

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]