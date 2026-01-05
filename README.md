# CardForge

> 打造你的专属角色 - SillyTavern 角色卡一站式工作台

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node.js](https://img.shields.io/badge/node.js-20+-green.svg)

CardForge 是一个为 SillyTavern (酒馆) 玩家和创作者设计的现代化 Web 工具。

它不仅是一个**角色卡编辑器**，更是一个**灵感孵化器**。无论你是想从零开始构思一个新角色，还是通过 AI 润色已有的设定，亦或是需要在不同格式间进行转换，CardForge 都能帮你轻松搞定。我们致力于简化繁琐的技术细节，让你专注于创作本身。

## ✨ 核心功能

### 🛠️ 全能工作台 (Workshop)
- **零门槛编辑**: 直观的表单设计，无需了解 JSON 结构即可修改姓名、描述、开场白等所有细节。
- **所见即所得 (WYSIWYG)**: 独有的**即时预览**模式，让你在保存前就能确认开场白、备选问候语在酒馆界面中的真实显示效果。
- **智能辅助**: 内置 Token 消耗估算、敏感词清洗建议，以及自动保存功能，防止意外丢失进度。
- **格式自由**: 无论是标准的 CCv3 PNG，还是古早的 V2 格式，甚至直接粘贴 JSON，全都能识别、能编辑、能导出。

### 🤖 AI 灵感助手
- **从零到一**: 仅需输入一个模糊的概念（如“自带反差属性的冷面杀手”），AI 即可为你生成包含性格、外貌、背景故事的完整设定。
- **旧卡焕新**: 拥有很多老旧的简单卡片？使用“智能润色”功能，一键扩写描述、丰富细节，让它们焕发新生。
- **多语言无障碍**: 一键翻译功能，轻松将外语角色卡转化为流畅的中文，或者将中文卡片国际化。
- **开场白工坊**: 只有一句开场白太单调？“开场白裂变”能基于人设自动生成多种不同情境、不同语气的备选开场白，让对话更丰富。

### 🦆 Quack 无损迁移
- **打破壁垒**: 独家支持导入 Quack 格式的角色数据，即使原站 API 受限，也能通过手动粘贴 JSON 完成迁移。
- **完美复刻**: 不仅仅是文字，更能完美保留 **HTML 样式排版** 和 **世界书 (Lorebook)** 关联，确保导入后的体验原汁原味。
- **自动转换**: 导入即转为通用的 SillyTavern V3 PNG 格式，让你的 Quack 角色卡可以在任何支持标准格式的酒馆前端中使用。

## 🚀 快速开始

我们提供了多种运行方式，首推 **Docker** 以获得最省心的体验。

### 🐳 Docker 部署 (推荐)

无需配置 Python 或 Node.js 环境，直接运行：

#### 方式一：使用预构建镜像（最快）

```bash
# Docker Hub
docker run -d -p 8000:8000 --name cardforge shizukuyume/cardforge:latest

# 或者 GitHub Container Registry
docker run -d -p 8000:8000 --name cardforge ghcr.io/shizukuyume/cardforge:latest
```

#### 方式二：从源码构建

```bash
# 1. 克隆项目
git clone https://github.com/ShizukuYume/cardforge.git
cd cardforge

# 2. 启动服务
docker compose -f docker/docker-compose.yml up -d
```

浏览器打开 http://localhost:8000 即可使用。

#### 镜像标签说明

| 标签 | 说明 |
|------|------|
| `latest` | 最新稳定版本 (main 分支) |
| `v1.0.0` | 特定版本号 |
| `<commit-sha>` | 特定提交构建 |

### 💻 本地开发运行

如果你是开发者，或者希望进行二次开发：

```bash
# 1. 启动后端 (Python 3.11+)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. 启动前端 (Node.js 20+)
cd frontend
npm install
npm run dev
```

## 📖 文档

更详细的使用说明请查阅文档目录：

- [⚡ 快速开始](docs/QUICKSTART.md) - 10分钟上手指南
- [📚 用户手册](docs/USER_GUIDE.md) - 完整功能深度解析
- [🔧 部署指南](docs/DEPLOYMENT.md) - 环境变量与生产环境配置
- [🔌 API 文档](docs/API.md) - 开发者 API 参考

## 🛠️ 技术栈

CardForge 采用现代化的前后端分离架构，确保了高性能与易维护性。

- **Frontend**: Vite + TailwindCSS + Alpine.js (轻量级、响应迅速)
- **Backend**: FastAPI (Python) + Pillow (图像处理)
- **Infrastructure**: Docker + Nginx

## 📝 支持的格式

| 格式 | 读取 | 写入 | 说明 |
|------|:----:|:----:|------|
| CCv3 PNG | ✅ | ✅ | 目前最通用的标准格式，支持完整元数据 |
| CCv2 PNG | ✅ | ✅ | 兼容旧版 SillyTavern 格式 |
| JSON | ✅ | ✅ | 纯数据格式，便于手动编辑 |
| Quack | ✅ | - | 专有格式导入，支持样式保留 |

> 💡 提示：所有的导出文件都会自动转换为标准 CCv3 PNG，确保在任何主流酒馆前端中都能完美使用。

## 🤝 贡献

CardForge 是一个开源项目，我们非常欢迎社区的参与。

无论是提交 Bug、建议新功能，还是直接提交 Pull Request，你的每一份贡献都让这个工具变得更好。如果你觉得这个项目对你有帮助，欢迎点一个 Star ⭐️！

## 📄 License

[MIT](LICENSE)
