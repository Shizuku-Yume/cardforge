# CardForge 快速开始

## 环境要求

- Python 3.11+
- Node.js 20+（仅开发模式需要）
- Docker（推荐用于部署）

---

## 方式一：Docker 部署（推荐）

### 使用预构建镜像（最快）

```bash
# Docker Hub
docker run -d -p 8000:8000 --name cardforge shizukuyume/cardforge:latest

# 或者 GitHub Container Registry
docker run -d -p 8000:8000 --name cardforge ghcr.io/shizukuyume/cardforge:latest

# 验证
curl http://localhost:8000/api/health
# 应返回 {"status":"healthy","version":"1.0.0"}

# 访问应用
open http://localhost:8000
```

### 从源码构建

```bash
# 克隆项目
git clone https://github.com/ShizukuYume/cardforge.git
cd cardforge

# 启动服务
docker compose -f docker/docker-compose.yml up -d
```

---

## 方式二：本地开发

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 访问应用

- 前端开发服务器: http://localhost:3000
- API 文档: http://localhost:8000/docs

---

## 功能一览

### 📦 工作台
- 上传 PNG/JSON 角色卡
- 编辑角色基础信息、描述、消息、系统设置
- 管理世界书条目
- 导出新的 PNG/JSON 卡片

### 🦆 Quack 导入
- 从 Quack 平台导入角色
- 支持 API 模式和手动 JSON 粘贴
- 自动转换为 CCv3 格式

### 🤖 AI 辅助
- 一句话生成完整角色卡
- 开场白裂变生成
- 卡片翻译
- 旧卡焕新优化

---

## 常见问题

### Q: 支持哪些格式？

支持 SillyTavern CCv3/V2 PNG 卡片和 JSON 格式。

### Q: HTML 格式会被保留吗？

是的，所有 HTML 内容在存储和导出时保持原样。

### Q: API Key 存储在哪里？

API Key 仅存储在浏览器本地 (LocalStorage)，不会发送到服务器存储。

---

## 下一步

- 查看 [用户手册](USER_GUIDE.md) 了解完整功能
- 查看 [部署指南](DEPLOYMENT.md) 了解生产环境配置
