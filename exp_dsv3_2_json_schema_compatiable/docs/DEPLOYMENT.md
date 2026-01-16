# DeepSeek V3.2 JSON Schema API - 完整部署指南

本文档提供完整的部署指南，包括本地开发、Docker部署、生产环境配置和云服务部署。

---

## 目录

1. [系统要求](#系统要求)
2. [快速开始](#快速开始)
3. [本地开发部署](#本地开发部署)
4. [Docker部署（推荐）](#docker部署推荐)
5. [生产环境部署](#生产环境部署)
6. [云服务部署](#云服务部署)
7. [监控与日志](#监控与日志)
8. [故障排除](#故障排除)
9. [安全建议](#安全建议)
10. [性能优化](#性能优化)

---

## 系统要求

### 最低配置
- **Python**: 3.13+
- **内存**: 512MB
- **磁盘**: 500MB
- **网络**: 能够访问 `https://api.deepseek.com`

### 推荐配置（生产环境）
- **CPU**: 2核+
- **内存**: 2GB+
- **磁盘**: 5GB+
- **网络**: 稳定的互联网连接
- **操作系统**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)

---

## 快速开始

### 5分钟快速部署（Docker Compose）

```bash
# 1. 克隆项目
git clone <repository-url>
cd exp_dsv3_2_json_schema_compatiable

# 2. 配置环境变量
cp .env.example .env
nano .env  # 编辑 DEEPSEEK_API_KEY

# 3. 启动服务
docker-compose up -d

# 4. 验证部署
curl http://localhost:8000/health

# 5. 查看日志
docker-compose logs -f api
```

**完成！** 服务现在运行在 http://localhost:8000

访问 http://localhost:8000/docs 查看完整API文档。

---

## Prerequisites / 前置要求

- Python 3.13+
- Docker and Docker Compose (for containerized deployment)
- DeepSeek API Key

## 本地开发部署 / Local Development

### 1. 环境准备 / Environment Setup

```bash
# 创建虚拟环境 / Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows: venv\\Scripts\\activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 开发环境额外依赖 / For development
pip install -r requirements-dev.txt
```

**中国用户镜像加速（可选）：**

```bash
# 使用清华镜像加速 pip
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 然后安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量 / Configuration

```bash
# 复制环境变量模板 / Copy environment template
cp .env.example .env

# 编辑配置文件 / Edit .env file
nano .env  # 或使用 vim .env
```

**必须配置的环境变量：**

```bash
# 最小配置 / Minimal configuration
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxx  # 必须替换为你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
```

**完整配置示例：**

```bash
# DeepSeek API配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
DEEPSEEK_TIMEOUT=30
DEEPSEEK_MAX_RETRIES=3

# 应用配置
APP_NAME=DeepSeek V3.2 JSON Schema API
APP_VERSION=1.0.0
DEBUG=true  # 开发环境设为true

# 服务器配置
HOST=0.0.0.0
PORT=8000
WORKERS=1  # 开发环境使用1个worker

# 日志配置
LOG_LEVEL=DEBUG  # 开发环境使用DEBUG
LOG_FORMAT=text  # 文本格式便于阅读
```

### 3. 运行测试 / Run Tests

```bash
# 运行所有测试 / Run all tests
pytest tests/ -v --cov=app --cov-report=html

# 查看测试覆盖率报告 / View coverage report
# Linux: xdg-open htmlcov/index.html
# Mac: open htmlcov/index.html
```

### 4. 启动开发服务器 / Start Development Server

**方法1：使用启动脚本**

```bash
# 赋予执行权限
chmod +x scripts/start.sh

# 启动服务
./scripts/start.sh
```

**方法2：直接使用 uvicorn**

```bash
# 基础启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 带日志的启动
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level debug
```

**方法3：使用 Python 直接运行**

```bash
python -m app.main
```

### 5. 访问API / Access API

服务启动后，可以通过以下地址访问：

- **API根路径**: http://localhost:8000
- **Swagger UI** (交互式文档): http://localhost:8000/docs
- **ReDoc** (参考文档): http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 6. 验证安装 / Verify Installation

```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出
# {"status":"healthy","timestamp":"2025-01-15T12:00:00Z","version":"1.0.0"}

# 测试API端点
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Docker部署（推荐）/ Docker Deployment

Docker部署是生产环境的最佳选择，提供一致的运行环境和简单的管理方式。

### 使用Docker Compose（最简单）

#### 1. 准备环境文件

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（必须设置DEEPSEEK_API_KEY）
nano .env
```

#### 2. 构建并启动服务

```bash
# 构建镜像并启动服务（后台运行）
docker-compose up -d

# 查看启动日志
docker-compose logs -f api

# 查看服务状态
docker-compose ps
```

#### 3. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 查看完整日志
docker-compose logs --tail=100 -f api
```

#### 4. 管理服务

```bash
# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 重启服务
docker-compose restart

# 停止并删除容器
docker-compose down

# 停止并删除容器+卷
docker-compose down -v

# 重新构建并启动（代码更新后）
docker-compose up -d --build

# 查看资源使用情况
docker stats deepseek-api
```

### 使用Docker命令（高级）

#### 1. 构建镜像

```bash
# 构建镜像
docker build -t deepseek-api:latest .

# 查看镜像
docker images | grep deepseek-api
```

#### 2. 运行容器

**基础运行：**

```bash
docker run -d \
  --name deepseek-api \
  -p 8000:8000 \
  -e DEEPSEEK_API_KEY=your_api_key \
  -e DEEPSEEK_BASE_URL=https://api.deepseek.com/beta \
  deepseek-api:latest
```

**完整配置运行：**

```bash
docker run -d \
  --name deepseek-api \
  -p 8000:8000 \
  -e DEEPSEEK_API_KEY=your_api_key \
  -e DEEPSEEK_BASE_URL=https://api.deepseek.com/beta \
  -e LOG_LEVEL=INFO \
  -e DEBUG=false \
  -e WORKERS=4 \
  --restart unless-stopped \
  --memory="1g" \
  --cpus="1.0" \
  --health-cmd "curl -f http://localhost:8000/health || exit 1" \
  --health-interval 30s \
  --health-timeout 10s \
  --health-retries 3 \
  deepseek-api:latest
```

**使用环境文件：**

```bash
docker run -d \
  --name deepseek-api \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  deepseek-api:latest
```

#### 3. 容器管理

```bash
# 查看运行中的容器
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 查看容器日志
docker logs -f deepseek-api

# 查看最后100行日志
docker logs --tail=100 deepseek-api

# 进入容器（调试用）
docker exec -it deepseek-api /bin/bash

# 在容器中执行命令
docker exec deepseek-api curl http://localhost:8000/health

# 停止容器
docker stop deepseek-api

# 启动已停止的容器
docker start deepseek-api

# 重启容器
docker restart deepseek-api

# 删除容器
docker rm deepseek-api

# 强制删除运行中的容器
docker rm -f deepseek-api

# 查看容器详细信息
docker inspect deepseek-api

# 查看容器资源使用
docker stats deepseek-api --no-stream
```

### Docker多阶段部署（生产环境优化）

创建优化的 `Dockerfile.prod`：

```dockerfile
# 构建阶段
FROM python:3.13-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.13-slim

WORKDIR /app

# 只复制必要的文件
COPY --from=builder /root/.local /root/.local
COPY ./app ./app
COPY pyproject.toml .

# 确保Python能找到安装的包
ENV PATH=/root/.local/bin:$PATH

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

构建并运行：

```bash
# 构建生产镜像
docker build -f Dockerfile.prod -t deepseek-api:prod .

# 运行生产容器
docker run -d \
  --name deepseek-api-prod \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  deepseek-api:prod
```

### Docker Compose多服务部署

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
      - LOG_LEVEL=INFO
      - DEBUG=false
      - WORKERS=4
    env_file:
      - .env
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - deepseek-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - deepseek-network

networks:
  deepseek-network:
    driver: bridge
```

部署：

```bash
# 部署生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
```

### Docker镜像管理

```bash
# 镜像标签管理
docker tag deepseek-api:latest deepseek-api:v1.0.0
docker tag deepseek-api:latest registry.example.com/deepseek-api:latest

# 推送到镜像仓库
docker login registry.example.com
docker push registry.example.com/deepseek-api:latest

# 推送到Docker Hub
docker tag deepseek-api:latest username/deepseek-api:latest
docker push username/deepseek-api:latest

# 清理无用镜像
docker image prune -a

# 查看镜像历史
docker history deepseek-api:latest
```

## 生产环境部署 / Production Deployment

生产环境需要考虑性能、可靠性、安全性等多个方面。以下是推荐的部署方案。

### 使用Gunicorn + Uvicorn（多进程部署）

Gunicorn是生产环境推荐的应用服务器，配合Uvicorn worker可以充分利用多核CPU。

#### 1. 安装Gunicorn

```bash
pip install gunicorn
```

#### 2. 创建Gunicorn配置文件

创建 `gunicorn_config.py`：

```python
# Gunicorn配置文件
import multiprocessing
import os

# 服务器socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker进程
# CPU密集型: (2 x CPU核心数) + 1
# I/O密集型（API调用）: CPU核心数 x 2~4
workers = int(os.environ.get("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # 自动重启worker，防止内存泄漏
max_requests_jitter = 50  # 随机抖动，避免所有worker同时重启
timeout = 30
keepalive = 2

# 日志
accesslog = "-"  # 输出到stdout
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "deepseek-api"

# 服务器机制
daemon = False  # 使用systemd管理，不要daemon
pidfile = "/tmp/gunicorn.pid"
umask = 0o007
user = None
group = None
tmp_upload_dir = None

# SSL（如果需要直接在Gunicorn层面使用SSL）
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# 预加载应用（节省内存，但代码更新需要重启）
preload_app = True

# 优雅重启
graceful_timeout = 30
```

#### 3. 启动服务

**使用配置文件启动：**

```bash
gunicorn -c gunicorn_config.py app.main:app
```

**命令行参数启动：**

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --timeout 30 \
  --keep-alive 2 \
  --max-requests 1000
```

#### 4. 使用Systemd管理服务

创建服务文件 `/etc/systemd/system/deepseek-api.service`：

```ini
[Unit]
Description=DeepSeek V3.2 JSON Schema API
Documentation=https://github.com/your-repo/deepseek-api
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=deepseek-api
WorkingDirectory=/opt/deepseek-api
Environment="PATH=/opt/deepseek-api/venv/bin"
EnvironmentFile=/opt/deepseek-api/.env

# 启动命令
ExecStart=/opt/deepseek-api/venv/bin/gunicorn \
    -c /opt/deepseek-api/gunicorn_config.py \
    app.main:app

# 重启配置
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/deepseek-api/logs
ReadWritePaths=/tmp

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

**部署步骤：**

```bash
# 1. 创建应用目录
sudo mkdir -p /opt/deepseek-api
sudo chown www-data:www-data /opt/deepseek-api

# 2. 复制应用文件
sudo cp -r . /opt/deepseek-api/
sudo chown -R www-data:www-data /opt/deepseek-api

# 3. 创建虚拟环境
cd /opt/deepseek-api
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/pip install gunicorn

# 4. 配置环境变量
sudo cp .env.example /opt/deepseek-api/.env
sudo nano /opt/deepseek-api/.env  # 编辑配置

# 5. 复制systemd服务文件
sudo cp deepseek-api.service /etc/systemd/system/

# 6. 重载systemd并启动服务
sudo systemctl daemon-reload
sudo systemctl enable deepseek-api
sudo systemctl start deepseek-api

# 7. 查看状态
sudo systemctl status deepseek-api

# 8. 查看日志
sudo journalctl -u deepseek-api -f
```

**管理命令：**

```bash
# 启动服务
sudo systemctl start deepseek-api

# 停止服务
sudo systemctl stop deepseek-api

# 重启服务
sudo systemctl restart deepseek-api

# 重新加载配置（不中断连接）
sudo systemctl reload deepseek-api

# 查看状态
sudo systemctl status deepseek-api

# 查看日志
sudo journalctl -u deepseek-api -f

# 查看最近100行日志
sudo journalctl -u deepseek-api -n 100

# 查看启动日志
sudo journalctl -u deepseek-api --since today

# 禁用服务
sudo systemctl disable deepseek-api

# 重新启用服务
sudo systemctl enable deepseek-api
```

### 使用Nginx反向代理

Nginx作为反向代理可以提供负载均衡、SSL终端、静态文件服务等功能。

#### 1. 安装Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx

# 启动Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 2. 配置反向代理

创建配置文件 `/etc/nginx/sites-available/deepseek-api`：

```nginx
# upstream配置（负载均衡）
upstream deepseek_backend {
    # 负载均衡算法：least_conn（最少连接）
    least_conn;

    # 后端服务器（可以配置多个）
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;

    # 保持连接
    keepalive 32;
}

# HTTP服务器（重定向到HTTPS）
server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;

    # Let's Encrypt验证
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # 其他请求重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS服务器
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/api.yourdomain.com/chain.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 日志
    access_log /var/log/nginx/deepseek-api-access.log;
    error_log /var/log/nginx/deepseek-api-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    # 主要location
    location / {
        # 代理传递
        proxy_pass http://deepseek_backend;

        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 缓冲禁用（实时API）
        proxy_buffering off;
    }

    # 健康检查端点（无需认证）
    location /health {
        proxy_pass http://deepseek_backend/health;
        access_log off;
    }

    # API文档（生产环境可以禁用或添加认证）
    location /docs {
        proxy_pass http://deepseek_backend/docs;
        # 可以添加认证：
        # auth_basic "API Documentation";
        # auth_basic_user_file /etc/nginx/.htpasswd;
    }

    location /redoc {
        proxy_pass http://deepseek_backend/redoc;
    }

    location /openapi.json {
        proxy_pass http://deepseek_backend/openapi.json;
    }
}
```

#### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/deepseek-api /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载Nginx
sudo systemctl reload nginx
```

#### 4. 配置HTTPS（使用Let's Encrypt）

```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书（自动配置Nginx）
sudo certbot --nginx -d api.yourdomain.com

# 测试自动续期
sudo certbot renew --dry-run

# 查看证书信息
sudo certbot certificates
```

### 使用Supervisor管理（替代方案）

如果不想使用systemd，可以使用Supervisor：

#### 1. 安装Supervisor

```bash
sudo apt install supervisor
```

#### 2. 配置Supervisor

创建 `/etc/supervisor/conf.d/deepseek-api.conf`：

```ini
[program:deepseek-api]
command=/opt/deepseek-api/venv/bin/gunicorn -c /opt/deepseek-api/gunicorn_config.py app.main:app
directory=/opt/deepseek-api
user=www-data
autostart=true
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/var/log/supervisor/deepseek-api.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=DEEPSEEK_API_KEY="your_api_key"

[group:deepseek-api]
programs=deepseek-api
```

#### 3. 管理服务

```bash
# 更新配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start deepseek-api

# 停止服务
sudo supervisorctl stop deepseek-api

# 重启服务
sudo supervisorctl restart deepseek-api

# 查看状态
sudo supervisorctl status

# 查看日志
sudo supervisorctl tail -f deepseek-api
```

### Using Systemd

Create service file `/etc/systemd/system/deepseek-api.service`:

```ini
[Unit]
Description=DeepSeek API Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/deepseek-api
Environment="PATH=/opt/deepseek-api/venv/bin"
EnvironmentFile=/opt/deepseek-api/.env
ExecStart=/opt/deepseek-api/venv/bin/gunicorn \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 0.0.0.0:8000 \\
    --access-logfile /var/log/deepseek-api/access.log \\
    --error-logfile /var/log/deepseek-api/error.log \\
    --log-level info \\
    app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable deepseek-api

# Start service
sudo systemctl start deepseek-api

# Check status
sudo systemctl status deepseek-api

# View logs
sudo journalctl -u deepseek-api -f
```

### Using Nginx Reverse Proxy

Nginx configuration `/etc/nginx/sites-available/deepseek-api`:

```nginx
upstream deepseek_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect to HTTPS (uncomment in production)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://deepseek_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# HTTPS configuration (uncomment in production)
# server {
#     listen 443 ssl http2;
#     server_name api.example.com;
#
#     ssl_certificate /path/to/cert.pem;
#     ssl_certificate_key /path/to/key.pem;
#
#     location / {
#         proxy_pass http://deepseek_api;
#         # ... same proxy settings as above
#     }
# }
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/deepseek-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Health Checks and Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:00:00Z",
  "version": "1.0.0"
}
```

### Monitoring Metrics

The service includes structured logging. Example log entry:

```json
{
  "event": "Incoming request",
  "request_id": "uuid",
  "method": "POST",
  "url": "http://localhost:8000/api/v1/chat/completions",
  "client": "127.0.0.1",
  "app": "DeepSeek V3.2 JSON Schema API",
  "version": "1.0.0",
  "timestamp": "2025-01-15T12:00:00Z"
}
```

## Security Best Practices

### 1. Environment Variables

- Never commit `.env` file to version control
- Use strong, random API keys
- Rotate API keys regularly
- Use different keys for development and production

### 2. Network Security

- Use HTTPS in production
- Implement rate limiting
- Configure firewall rules
- Use VPN or private networks for admin access

### 3. Application Security

- Set `DEBUG=false` in production
- Implement authentication/authorization
- Validate all inputs
- Keep dependencies updated
- Regular security audits

### 4. Rate Limiting

Install slowapi:

```bash
pip install slowapi
```

Add to `app/main.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Add to endpoint
@router.post("/completions")
@limiter.limit("10/minute")
async def create_chat_completion(...):
    ...
```

## Performance Tuning

### Worker Count

For CPU-intensive tasks:
```bash
# Number of CPU cores
workers=$(nproc)
```

For I/O-intensive tasks (API calls):
```bash
# 2-4x number of CPU cores
workers=$(($(nproc) * 2))
```

### Connection Pooling

The OpenAI client is configured with connection pooling:

```python
http_client=httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    )
)
```

Adjust based on your load.

### Caching

Consider caching validated schemas:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def validate_schema_cached(schema_hash: str):
    # Validation logic
    pass
```

## Troubleshooting

### Common Issues

1. **Port already in use:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

2. **API key errors:**
```bash
# Verify .env file is loaded
cat .env

# Check logs for errors
docker-compose logs -f api
```

3. **Out of memory:**
```bash
# Reduce workers
export WORKERS=2

# Or increase Docker memory limit
docker run -m 512m ...
```

4. **Slow responses:**
- Check DeepSeek API status
- Verify network connectivity
- Check logs for errors
- Monitor resource usage

### Log Locations

- Application logs: Check stdout/stderr or configure file logging
- Nginx logs: `/var/log/nginx/`
- Systemd logs: `journalctl -u deepseek-api`

## Backup and Recovery

### Backup

```bash
# Backup source code
tar -czf deepseek-api-$(date +%Y%m%d).tar.gz .

# Backup environment file
cp .env .env.backup
```

### Recovery

```bash
# Extract backup
tar -xzf deepseek-api-20250115.tar.gz

# Restore environment
cp .env.backup .env

# Restart service
sudo systemctl restart deepseek-api
```

## Updates and Maintenance

### Update Dependencies

```bash
# Update requirements
pip install --upgrade -r requirements.txt

# Test after update
pytest tests/

# Restart service
sudo systemctl restart deepseek-api
```

### Rolling Updates (Docker)

```bash
# Pull new image
docker pull deepseek-api:latest

# Update with zero downtime
docker-compose up -d --no-deps --build api
```

## 云服务部署 / Cloud Deployment

### AWS部署（Amazon Web Services）

#### 使用AWS ECS（Elastic Container Service）

**1. 创建ECR仓库**

```bash
# 登录ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 构建镜像
docker build -t deepseek-api .

# 标记镜像
docker tag deepseek-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/deepseek-api:latest

# 推送镜像
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/deepseek-api:latest
```

**2. 创建任务定义** `ecs-task-definition.json`

```json
{
  "family": "deepseek-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "deepseek-api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/deepseek-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEEPSEEK_BASE_URL",
          "value": "https://api.deepseek.com/beta"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "WORKERS",
          "value": "4"
        }
      ],
      "secrets": [
        {
          "name": "DEEPSEEK_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:deepseek/api-key-xxxxx"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/deepseek-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**3. 注册任务定义**

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

**4. 创建ECS服务**

```bash
aws ecs create-service \
  --cluster deepseek-cluster \
  --service-name deepseek-api \
  --task-definition deepseek-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx,subnet-yyyyy],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
  --health-check-grace-period-seconds 60
```

**5. 创建Application Load Balancer**

```bash
# 创建目标组
aws elbv2 create-target-group \
  --name deepseek-api-tg \
  --protocol HTTP \
  --port 8000 \
  --target-type ip \
  --vpc-id vpc-xxxxx \
  --health-check Path=/health,IntervalSeconds=30,TimeoutSeconds=5,HealthyThreshold=3,UnhealthyThreshold=2

# 创建负载均衡器
aws elbv2 create-load-balancer \
  --name deepseek-api-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx \
  --scheme internet-facing

# 创建监听器
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:<account-id>:loadbalancer/net/deepseek-api-alb/xxxxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/deepseek-api-tg/xxxxx
```

#### 使用AWS Elastic Beanstalk

**1. 安装EB CLI**

```bash
pip install awsebcli
```

**2. 初始化项目**

```bash
eb init -p python deepseek-api \
  --region us-east-1 \
  --keyname my-aws-keypair
```

**3. 创建环境**

```bash
eb create production-env \
  --single \
  --instance-type t3.medium \
  --scale 2 \
  --timeout 15
```

**4. 部署**

```bash
eb deploy
```

**5. 查看日志**

```bash
eb logs --all
eb ssh
```

### 阿里云部署

#### 使用ACK（阿里云Kubernetes）

**1. 创建Kubernetes集群**

在阿里云控制台创建ACK集群或使用CLI：

```bash
# 创建托管Kubernetes集群
aliyun cs POST /clusters \
  --body '{
    "name": "deepseek-api-cluster",
    "region_id": "cn-hangzhou",
    "cluster_type": "ManagedKubernetes",
    "kubernetes_version": "1.28.3",
    "node_cidr_mask": "25",
    "service_cidr": "172.21.0.0/20",
    "vpcid": "vpc-xxxxx",
    "vswitch_ids": ["vsw-xxxxx"],
    "master_count": 3,
    "master_vswitch_ids": ["vsw-xxxxx", "vsw-yyyyy", "vsw-zzzzz"],
    "master_instance_types": ["ecs.c6.xlarge"],
    "worker_instance_types": ["ecs.c6.xlarge"],
    "num_of_nodes": 2,
    "enable_ssh": true
  }'
```

**2. 配置kubectl**

```bash
# 获取kubeconfig
aliyun cs GET /k8s/xxxxx/user_config | kubectl config use-context xxxxx

# 验证连接
kubectl get nodes
```

**3. 创建部署配置** `deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deepseek-api
  namespace: default
  labels:
    app: deepseek-api
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: deepseek-api
  template:
    metadata:
      labels:
        app: deepseek-api
        version: v1
    spec:
      containers:
      - name: deepseek-api
        image: registry.cn-hangzhou.aliyuncs.com/your-namespace/deepseek-api:latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: DEEPSEEK_BASE_URL
          value: "https://api.deepseek.com/beta"
        - name: DEEPSEEK_API_KEY
          valueFrom:
            secretKeyRef:
              name: deepseek-secrets
              key: api-key
        - name: LOG_LEVEL
          value: "INFO"
        - name: WORKERS
          value: "4"
        - name: DEBUG
          value: "false"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: deepseek-api-service
  namespace: default
  labels:
    app: deepseek-api
spec:
  type: LoadBalancer
  selector:
    app: deepseek-api
  ports:
  - name: http
    protocol: TCP
    port: 80
    targetPort: 8000
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
---
apiVersion: v1
kind: Secret
metadata:
  name: deepseek-secrets
  namespace: default
type: Opaque
stringData:
  api-key: "sk-xxxxxxxxxxxxxxxxxx"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: deepseek-api-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: deepseek-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 15
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

**4. 部署到K8s**

```bash
# 部署应用
kubectl apply -f deployment.yaml

# 查看状态
kubectl get pods -l app=deepseek-api
kubectl get svc deepseek-api-service
kubectl get hpa deepseek-api-hpa

# 查看日志
kubectl logs -l app=deepseek-api --tail=100 -f

# 扩缩容
kubectl scale deployment deepseek-api --replicas=5

# 查看事件
kubectl get events --sort-by='.lastTimestamp'
```

#### 使用阿里云ECS直接部署

**1. 购买ECS实例**

- 实例规格：ecs.c6.xlarge（4核8G）或更高
- 镜像：Ubuntu 20.04 或 CentOS 8
- 网络：VPC，分配公网IP
- 安全组：开放80、443、8000端口

**2. 连接服务器**

```bash
ssh root@your-server-ip
```

**3. 安装Docker**

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 启动Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**4. 部署应用**

```bash
# 克隆代码
git clone <repository-url>
cd exp_dsv3_2_json_schema_compatiable

# 配置环境变量
cp .env.example .env
nano .env

# 启动服务
docker-compose up -d

# 配置防火墙
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

### 腾讯云部署

#### 使用腾讯云CVM + Docker

**1. 创建CVM实例**

- 实例类型：S5.MEDIUM4（2核4G）或更高
- 镜像：Ubuntu 20.04
- 网络：VPC，分配公网IP
- 安全组：开放80、443端口

**2. 部署应用**

```bash
# 连接服务器
ssh ubuntu@your-server-ip

# 安装Docker
curl -fsSL https://get.docker.com | sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 部署应用
git clone <repository-url>
cd exp_dsv3_2_json_schema_compatiable
docker-compose up -d
```

#### 使用腾讯云TKE（Kubernetes）

类似于阿里云ACK，使用kubectl部署到TKE集群。

---

## 监控与日志 / Monitoring and Logging

### 日志配置

#### 1. JSON格式日志（生产环境推荐）

```bash
# .env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

JSON格式日志示例：

```json
{
  "timestamp": "2025-01-15T12:00:00Z",
  "level": "info",
  "event": "incoming_request",
  "request_id": "abc123",
  "method": "POST",
  "path": "/api/v1/chat/completions",
  "status_code": 200,
  "duration_ms": 1234,
  "client_ip": "1.2.3.4",
  "user_agent": "Python/3.9"
}
```

#### 2. 文本格式日志（开发环境）

```bash
# .env
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

### 日志聚合方案

#### 1. ELK Stack（Elasticsearch + Logstash + Kibana）

创建 `docker-compose.logging.yml`：

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - logging

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
    networks:
      - logging

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - logging

volumes:
  elasticsearch_data:

networks:
  logging:
    driver: bridge
```

创建Logstash配置 `logstash/pipeline/logstash.conf`：

```conf
input {
  tcp {
    port => 5044
    codec => json
  }
}

filter {
  # 解析JSON日志
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }

  # 添加时间戳
  date {
    match => ["timestamp", "ISO8601"]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "deepseek-api-%{+YYYY.MM.dd}"
  }
}
```

启动日志系统：

```bash
docker-compose -f docker-compose.logging.yml up -d
```

#### 2. 使用阿里云日志服务SLS

```python
# 在 app/core/logger.py 中添加阿里云SLS支持
from aliyun.log import LogClient

# 配置
endpoint = 'cn-hangzhou.log.aliyuncs.com'
accessKeyId = os.getenv('ALIYUN_ACCESS_KEY_ID')
accessKey = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
project = 'deepseek-api'
logstore = 'api-logs'

# 创建客户端
client = LogClient(endpoint, accessKeyId, accessKey)

# 发送日志
def send_to_aliyun_sls(log_data):
    client.put_logs(project, logstore, log_data)
```

### 性能监控

#### 1. Prometheus + Grafana

**在 `app/main.py` 中添加Prometheus端点：**

```bash
# 安装依赖
pip install prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

# 在app创建后添加
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Prometheus配置** `prometheus.yml`：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'deepseek-api'
    static_configs:
      - targets: ['deepseek-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

**Grafana仪表板配置**

创建 `grafana/dashboards/dashboard.json` 或使用Grafana UI导入。

#### 2. 阿里云CloudMonitor

```python
# 上报自定义指标到阿里云云监控
from aliyunsdkcore.client import AcsClient
from aliyunsdkcms.request.v20190101.PutCustomMetricRequest import PutCustomMetricRequest

def report_metric_to_aliyun(metric_name, value, dimensions={}):
    client = AcsClient(
        os.getenv('ALIYUN_ACCESS_KEY_ID'),
        os.getenv('ALIYUN_ACCESS_KEY_SECRET'),
        'cn-hangzhou'
    )

    request = PutCustomMetricRequest()
    request.set_MetricName(metric_name)
    request.set_Value(value)
    request.set_Dimensions(dimensions)

    response = client.do_action_with_exception(request)
    return response
```

### 健康检查与告警

#### 1. 创建监控脚本 `scripts/monitor.sh`：

```bash
#!/bin/bash

ENDPOINT="http://localhost:8000/health"
ALERT_EMAIL="admin@yourdomain.com"
DISCORD_WEBHOOK="https://discord.com/api/webhooks/xxx"

while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ENDPOINT)
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

    if [ $STATUS -ne 200 ]; then
        MESSAGE="[ALERT $TIMESTAMP] Health check failed with status $STATUS"
        echo $MESSAGE

        # 发送邮件
        echo "DeepSeek API health check failed" | mail -s "API Alert" $ALERT_EMAIL

        # 发送Discord通知
        curl -X POST $DISCORD_WEBHOOK \
          -H "Content-Type: application/json" \
          -d "{\"content\": \"❌ $MESSAGE\"}"
    fi

    sleep 60
done
```

#### 2. 使用systemd管理监控服务

创建 `/etc/systemd/system/deepseek-monitor.service`：

```ini
[Unit]
Description=DeepSeek API Health Monitor
After=network.target

[Service]
Type=simple
User=monitor
WorkingDirectory=/opt/deepseek-api
ExecStart=/opt/deepseek-api/scripts/monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 故障排除 / Troubleshooting

### 常见问题诊断流程

#### 问题1：服务无法启动

**症状：**
- 访问 http://localhost:8000 返回连接拒绝
- docker-compose logs 显示启动错误

**诊断步骤：**

```bash
# 1. 检查端口是否被占用
sudo lsof -i :8000
netstat -tulpn | grep 8000

# 2. 查看详细日志
docker-compose logs --tail=100 api
# 或
journalctl -u deepseek-api -n 100

# 3. 检查环境变量
docker-compose config
# 或
cat /opt/deepseek-api/.env

# 4. 验证配置文件
docker-compose config
```

**解决方案：**

```bash
# 方案1：杀死占用端口的进程
sudo kill -9 <PID>

# 方案2：更改端口
# .env
PORT=8888

# 方案3：检查依赖
pip install -r requirements.txt
```

#### 问题2：API返回401/403错误

**症状：**
- 调用DeepSeek API返回认证错误
- 日志显示 "Invalid API key"

**诊断步骤：**

```bash
# 1. 检查API密钥
echo $DEEPSEEK_API_KEY
cat .env | grep DEEPSEEK_API_KEY

# 2. 测试API密钥有效性
curl -X POST https://api.deepseek.com/beta/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "test"}]
  }'

# 3. 检查Base URL
echo $DEEPSEEK_BASE_URL
```

**解决方案：**

```bash
# 更新API密钥
nano .env
# DEEPSEEK_API_KEY=your_new_api_key

# 重启服务
docker-compose restart
# 或
sudo systemctl restart deepseek-api
```

#### 问题3：Schema验证失败（422错误）

**症状：**
- 返回 "422 Unprocessable Entity"
- 错误信息：Schema validation failed

**诊断步骤：**

```bash
# 1. 检查请求schema
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "test"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "test",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {"name": {"type": "string", "minLength": 2}},
          "required": ["name"]
        }
      }
    }]
  }' -v

# 2. 查看错误详情
docker-compose logs api | grep "validation"
```

**解决方案：**

服务会自动移除不支持的属性，确保schema符合DeepSeek要求。如果仍有问题：

1. 确保 `additionalProperties: false`
2. 确保所有properties都在required中
3. 移除minLength、maxLength等不支持的属性

#### 问题4：内存不足（OOM Killer）

**症状：**
- 容器/进程突然退出
- 日志显示 "Out of memory"

**诊断步骤：**

```bash
# 1. 检查内存使用
free -h
docker stats
top

# 2. 查看OOM日志
sudo dmesg | grep -i "out of memory"
sudo journalctl -k | grep -i "oom"

# 3. 查看应用内存使用
ps aux --sort=-%mem | head
```

**解决方案：**

```bash
# 方案1：减少workers
# .env
WORKERS=2

# 方案2：增加内存限制
docker run -m 2g ...
# 或
# gunicorn_config.py
workers = 2

# 方案3：添加swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 问题5：响应超时

**症状：**
- 请求长时间无响应
- 返回 504 Gateway Timeout

**诊断步骤：**

```bash
# 1. 检查DeepSeek API状态
curl -I https://api.deepseek.com

# 2. 测试网络连接
ping api.deepseek.com
traceroute api.deepseek.com

# 3. 查看应用日志
docker-compose logs -f api

# 4. 检查worker状态
ps aux | grep gunicorn
```

**解决方案：**

```bash
# 方案1：增加超时时间
# .env
DEEPSEEK_TIMEOUT=60

# 方案2：调整nginx超时
# nginx.conf
proxy_read_timeout 90s;
proxy_connect_timeout 90s;

# 方案3：增加workers
# .env
WORKERS=4
```

### 调试技巧

#### 1. 启用详细日志

```bash
# .env
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

#### 2. 使用Python调试器

```bash
# 安装ipdb
pip install ipdb

# 在代码中添加断点
import ipdb; ipdb.set_trace()
```

#### 3. 使用Docker exec调试

```bash
# 进入容器
docker exec -it deepseek-api /bin/bash

# 安装调试工具
apt-get update && apt-get install -y curl vim strace

# 追踪系统调用
strace -p <PID>

# 监控网络流量
tcpdump -i any port 8000
```

---

## 安全建议 / Security Best Practices

### 1. API密钥管理

**❌ 不要这样做：**

```python
# 硬编码API密钥
api_key = "sk-xxxxxxxx"  # 危险！

# 提交到版本控制
git add .env
git commit -m "Add api key"
```

**✅ 正确做法：**

```python
# 使用环境变量
import os
api_key = os.getenv("DEEPSEEK_API_KEY")

# 使用密钥管理服务
# AWS Secrets Manager
# Azure Key Vault
# HashiCorp Vault
```

### 2. HTTPS配置

#### 使用Let's Encrypt免费证书

```bash
# 安装certbot
sudo apt install certbot

# 获取证书（standalone模式）
sudo certbot certonly --standalone -d api.yourdomain.com

# 证书位置
# /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/api.yourdomain.com/privkey.pem
```

### 3. 限流保护

```python
# 在 app/main.py 中添加
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 应用到端点
@app.post("/api/v1/chat/completions")
@limiter.limit("60/minute")  # 每分钟60次
async def chat_completions(request: Request, ...):
    ...
```

### 4. CORS配置

```python
# 生产环境不要使用 "*"
# .env
ALLOWED_ORIGINS=["https://yourdomain.com", "https://app.yourdomain.com"]
```

### 5. 输入验证

```python
# 使用Pydantic进行严格的输入验证
# 所有端点都已经有Pydantic模型验证
```

### 6. 日志脱敏

```python
# 在日志中移除敏感信息
def sanitize_log(data: dict) -> dict:
    """移除日志中的敏感信息"""
    sensitive_keys = ['api_key', 'password', 'token', 'secret']
    return {k: v for k, v in data.items() if k not in sensitive_keys}
```

---

## 性能优化 / Performance Optimization

### 1. Worker数量优化

**计算公式：**

```bash
# CPU密集型
workers = $(($(nproc) * 2) + 1)

# I/O密集型（API调用场景）
workers = $(($(nproc) * 4))

# 实际测试确定最佳值
for workers in 2 4 8 16; do
  echo "Testing with $workers workers..."
  # 运行基准测试
done
```

### 2. 连接池配置

```python
# app/services/deepseek_client.py
import httpx

client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=5.0
    ),
    timeout=httpx.Timeout(30.0, connect=10.0)
)
```

### 3. 缓存策略

```python
# 缓存验证过的schema
from functools import lru_cache
import hashlib

@lru_cache(maxsize=128)
def validate_schema_cached(schema_str: str):
    schema = json.loads(schema_str)
    return validator.validate_schema(schema)

# 使用
schema_hash = hashlib.md5(json.dumps(schema).encode()).hexdigest()
is_valid, errors = validate_schema_cached(schema_hash)
```

---

## 部署检查清单 / Deployment Checklist

### 部署前检查

- [ ] 配置 `.env` 文件（特别是 `DEEPSEEK_API_KEY`）
- [ ] 安装所有依赖（`pip install -r requirements.txt`）
- [ ] 测试本地启动（`python -m app.main` 或 `uvicorn app.main:app`）
- [ ] 运行测试套件（`pytest tests/`）
- [ ] 健康检查通过（`curl http://localhost:8000/health`）
- [ ] API文档可访问（http://localhost:8000/docs）

### 生产环境检查

- [ ] 设置 `DEBUG=false`
- [ ] 配置HTTPS（SSL证书）
- [ ] 配置反向代理（Nginx）
- [ ] 设置防火墙规则
- [ ] 配置日志聚合
- [ ] 设置监控和告警
- [ ] 配置自动重启（systemd/docker restart policy）
- [ ] 配置备份策略
- [ ] 性能测试
- [ ] 安全审计

### 部署后验证

```bash
# 1. 健康检查
curl http://your-domain/health

# 2. API测试
curl -X POST http://your-domain/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# 3. Schema转换测试
curl -X POST http://your-domain/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Weather in Beijing"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string", "minLength": 2}
          },
          "required": ["location"],
          "additionalProperties": false
        }
      }
    }]
  }'

# 4. 查看日志
docker-compose logs -f api
# 或
sudo journalctl -u deepseek-api -f

# 5. 监控资源
docker stats
# 或
htop
```

---

## 常见问题FAQ / Frequently Asked Questions

### Q1: Docker容器启动后立即退出？

**A:** 检查日志查看退出原因：

```bash
docker-compose logs api
```

常见原因：
- `.env` 文件配置错误
- 依赖安装不完整
- 端口冲突

### Q2: 如何查看实时日志？

**A:**

```bash
# Docker
docker-compose logs -f api

# Systemd
sudo journalctl -u deepseek-api -f

# Kubernetes
kubectl logs -f deployment/deepseek-api
```

### Q3: 如何更新应用？

**A:**

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 或使用systemd
cd /opt/deepseek-api
sudo -u www-data git pull
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo systemctl restart deepseek-api
```

### Q4: 如何备份数据？

**A:**

```bash
# 备份配置
tar -czf backup-$(date +%Y%m%d).tar.gz \
  .env \
  docker-compose.yml \
  nginx.conf

# 备份到远程服务器
scp backup-*.tar.gz user@backup-server:/backups/
```

### Q5: 如何优化成本？

**A:**
- 使用Fargate Spot实例（AWS）
- 使用抢占式实例（阿里云/腾讯云）
- 合理设置资源limits
- 启用自动扩缩容
- 使用预留实例

---

## 支持与帮助 / Support

### 获取帮助

- **API文档**: http://your-domain:8000/docs
- **健康检查**: http://your-domain:8000/health
- **项目README**: [README.md](../README.md)
- **OpenAI兼容性**: [OPENAI_COMPATIBILITY.md](../OPENAI_COMPATIBILITY.md)
- **测试报告**: [FINAL_TEST_REPORT.md](../FINAL_TEST_REPORT.md)

### 常用命令速查

```bash
# Docker
docker-compose up -d          # 启动
docker-compose down           # 停止
docker-compose logs -f api    # 查看日志
docker-compose restart        # 重启
docker-compose ps             # 状态

# Systemd
sudo systemctl start deepseek-api    # 启动
sudo systemctl stop deepseek-api     # 停止
sudo systemctl restart deepseek-api  # 重启
sudo systemctl status deepseek-api   # 状态
sudo journalctl -u deepseek-api -f   # 日志

# Kubernetes
kubectl apply -f deployment.yaml     # 部署
kubectl get pods                      # 查看Pods
kubectl logs -f deployment/deepseek-api  # 日志
kubectl scale deployment deepseek-api --replicas=3  # 扩容
```

---

**文档版本**: 2.0.0
**最后更新**: 2025-01-15
**维护者**: DeepSeek API Team
