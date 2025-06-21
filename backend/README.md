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
