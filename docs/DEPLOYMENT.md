# CardForge 部署指南

## 目录

- [本地开发](#本地开发)
- [Docker 部署](#docker-部署)
- [生产环境配置](#生产环境配置)
- [环境变量](#环境变量)
- [反向代理配置](#反向代理配置)
- [安全建议](#安全建议)
- [故障排查](#故障排查)

---

## 本地开发

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

访问 http://localhost:3000 查看前端页面。

### 运行测试

```bash
# 后端测试
cd backend
pytest tests/ -v

# 后端测试覆盖率
pytest tests/ -v --cov=app --cov-report=html
```

---

## Docker 部署

### 快速开始（使用预构建镜像）

最快的方式是直接使用预构建镜像：

```bash
# Docker Hub
docker run -d -p 8000:8000 --name cardforge shizukuyume/cardforge:latest

# 或者 GitHub Container Registry
docker run -d -p 8000:8000 --name cardforge ghcr.io/shizukuyume/cardforge:latest
```

应用将在 http://localhost:8000 上可用。

#### 可用镜像标签

| 标签 | 说明 |
|------|------|
| `latest` | 最新稳定版本 (main 分支) |
| `v1.0.0` | 特定版本号 |
| `<commit-sha>` | 特定提交构建 |

### 从源码构建

```bash
# 克隆项目
git clone https://github.com/ShizukuYume/cardforge.git
cd cardforge

# 使用 Docker Compose 构建并运行
docker compose -f docker/docker-compose.yml up -d
```

### 单独构建镜像

```bash
# 从项目根目录构建
docker build -t cardforge:latest -f docker/Dockerfile .

# 运行容器
docker run -d \
  --name cardforge \
  -p 8000:8000 \
  -e CARDFORGE_LOG_REDACT=true \
  cardforge:latest
```

### 查看日志

```bash
# 实时查看日志
docker logs -f cardforge

# 查看最近 100 行
docker logs --tail 100 cardforge
```

### 停止和删除

```bash
# 停止
docker compose -f docker/docker-compose.yml down

# 停止并删除数据卷
docker compose -f docker/docker-compose.yml down -v
```

---

## 生产环境配置

### 1. 复制环境变量模板

```bash
cp docker/.env.production .env
```

### 2. 编辑环境变量

```bash
# 编辑 .env 文件
nano .env
```

### 3. 使用环境变量启动

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CARDFORGE_APP_VERSION` | `0.1.0` | 应用版本号 |
| `CARDFORGE_DEBUG` | `false` | 调试模式（生产环境应为 false） |
| `CARDFORGE_MAX_UPLOAD_MB` | `20` | 最大上传文件大小 (MB) |
| `CARDFORGE_HTTP_TIMEOUT` | `30` | HTTP 请求超时 (秒) |
| `CARDFORGE_PROXY_ENABLED_DEFAULT` | `false` | 默认启用 AI 代理 |
| `CARDFORGE_PROXY_ALLOW_LOCALHOST` | `false` | 允许代理到 localhost（Ollama/LM Studio）|
| `CARDFORGE_RATE_LIMIT_REQUESTS` | `10` | 代理接口限流：每个 IP 最大请求数 |
| `CARDFORGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | 限流时间窗口 (秒) |
| `CARDFORGE_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR）|
| `CARDFORGE_LOG_REDACT` | `true` | 日志脱敏（隐藏 API Key/Cookie）|
| `CARDFORGE_CORS_ORIGINS` | `*` | CORS 允许的来源（逗号分隔，如 `https://example.com,https://app.example.com`）|
| `CARDFORGE_PORT` | `8000` | Docker 容器暴露端口 |

---

## 反向代理配置

### Nginx (推荐)

```nginx
# /etc/nginx/sites-available/cardforge
server {
    listen 80;
    server_name cardforge.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cardforge.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Upload size limit (match CARDFORGE_MAX_UPLOAD_MB)
    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support (for AI streaming)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # API health check
    location /api/health {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 5s;
    }
}
```

### Caddy

```caddyfile
cardforge.example.com {
    reverse_proxy localhost:8000 {
        # SSE support
        flush_interval -1
    }
    
    # Upload limit
    request_body {
        max_size 20MB
    }
}
```

---

## 安全建议

### 1. 生产环境必须

- ✅ 启用 HTTPS（使用反向代理）
- ✅ 保持 `CARDFORGE_LOG_REDACT=true`（日志脱敏）
- ✅ 设置合理的上传限制
- ✅ 配置速率限制

### 2. 强烈推荐

- ✅ 使用非 root 用户运行容器（Dockerfile 已配置）
- ✅ 限制容器资源（docker-compose.yml 已配置）
- ✅ 配置日志轮转（docker-compose.yml 已配置）
- ✅ 定期更新基础镜像

### 3. AI 代理安全

默认情况下，AI 代理只允许访问以下域名：
- `api.openai.com`
- `api.anthropic.com`
- `openrouter.ai`
- `generativelanguage.googleapis.com`

如需支持本地 LLM（Ollama/LM Studio），设置：
```bash
CARDFORGE_PROXY_ALLOW_LOCALHOST=true
```

⚠️ **警告**：仅在受信任环境中启用此选项。

### 4. CORS 配置

默认允许所有来源。生产环境建议限制：

```bash
# 在 .env 或 docker-compose.yml 中设置
CARDFORGE_CORS_ORIGINS=https://cardforge.example.com,https://app.example.com
```

---

## 故障排查

### 容器无法启动

```bash
# 查看启动日志
docker logs cardforge

# 常见原因：
# - 端口被占用：更改 CARDFORGE_PORT
# - 权限问题：检查目录权限
```

### 健康检查失败

```bash
# 手动检查健康端点
curl http://localhost:8000/api/health

# 预期响应：
# {"status":"healthy","version":"0.1.0"}
```

### AI 代理不工作

```bash
# 检查代理设置
curl -X POST http://localhost:8000/api/proxy/models \
  -H "Content-Type: application/json" \
  -d '{"base_url": "https://api.openai.com/v1", "api_key": "sk-xxx"}'

# 常见错误：
# - URL_NOT_ALLOWED: 目标 URL 不在白名单
# - RATE_LIMITED: 请求过于频繁
# - TIMEOUT: 上游服务超时
```

### 上传文件失败

```bash
# 检查文件大小限制
# 默认限制：20MB

# 如需增加，修改环境变量：
CARDFORGE_MAX_UPLOAD_MB=50

# 同时更新 nginx 配置：
client_max_body_size 50M;
```

### SSE 流式响应不工作

检查反向代理配置：
```nginx
# Nginx 必须禁用缓冲
proxy_buffering off;
proxy_cache off;
```

---

## 监控

### Prometheus 指标

CardForge 暂未内置 Prometheus 指标，可通过日志监控：

```bash
# 统计请求数
docker logs cardforge 2>&1 | grep -c "POST /api/cards/parse"
```

### 健康检查端点

```bash
# 用于负载均衡器
GET /api/health

# 响应格式
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## 更新升级

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker compose -f docker/docker-compose.yml build

# 3. 重启服务
docker compose -f docker/docker-compose.yml up -d

# 4. 验证
curl http://localhost:8000/api/health
```

---

## 备份与恢复

CardForge 是无状态应用，所有用户数据存储在浏览器 LocalStorage 中。

如需备份配置：
```bash
# 备份环境变量
cp .env .env.backup

# 备份 Docker 配置
cp docker/docker-compose.yml docker/docker-compose.yml.backup
```
