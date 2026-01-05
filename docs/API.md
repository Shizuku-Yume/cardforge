# CardForge API 文档

> 本文档记录 CardForge 后端 API 的详细规范。所有 API 端点以 `/api` 为前缀。
>
> 完整交互式文档请启动后端后访问 http://localhost:8000/docs

---

## 基础端点

### 健康检查

```http
GET /api/health
```

**响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### API 信息

```http
GET /api
```

**响应:**
```json
{
  "name": "CardForge",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

## 卡片操作

### 解析卡片

解析 PNG 或 JSON 文件为 CCv3 格式。

```http
POST /api/cards/parse
Content-Type: multipart/form-data

file: <PNG/JSON/JPG/WebP 文件>
```

**支持的格式:**
- PNG (ccv3/chara 元数据)
- JSON (CCv3/CCv2)
- JPG/WebP/GIF (仅作为卡面图片)

**响应:**
```json
{
  "success": true,
  "data": {
    "card": { /* CCv3 完整数据 */ },
    "source_format": "v3",
    "has_image": true,
    "image_base64": "data:image/png;base64,...",
    "token_breakdown": {
      "description": 150,
      "first_mes": 80,
      "total": 320
    },
    "warnings": []
  }
}
```

### 注入卡片

将 CCv3 数据注入到 PNG 图片中。

```http
POST /api/cards/inject
Content-Type: multipart/form-data

file: <PNG 图片>
card_data: <CCv3 JSON 字符串>
include_v2: <boolean, 可选，默认 true>
```

**响应:** PNG 文件下载

### 验证卡片

验证 CCv3 JSON 数据的格式正确性。

```http
POST /api/cards/validate
Content-Type: application/json

{
  "spec": "chara_card_v3",
  "spec_version": "3.0",
  "data": { /* CCv3 数据 */ }
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

---

## 世界书操作

### 导出世界书

将世界书导出为独立 JSON 文件。

```http
POST /api/lorebook/export
Content-Type: application/json

{
  "character_book": { /* 世界书数据 */ }
}
```

**响应:** JSON 文件下载

### 导入世界书

从 JSON 文件导入世界书。

```http
POST /api/lorebook/import
Content-Type: multipart/form-data

file: <JSON 文件>
```

**响应:**
```json
{
  "success": true,
  "data": {
    "character_book": { /* 世界书数据 */ },
    "entry_count": 10
  }
}
```

---

## Quack 导入

### 导入角色

从 Quack 平台导入角色数据。

```http
POST /api/quack/import
Content-Type: application/json

{
  "character_id": "角色ID或URL",
  "cookie": "Quack网站Cookie",
  "import_mode": "full",
  "output_format": "png"
}
```

**参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| `character_id` | string | 角色 ID 或完整 URL |
| `cookie` | string | Quack 登录 Cookie |
| `import_mode` | string | `full` (完整) 或 `lorebook_only` (仅世界书) |
| `output_format` | string | `png` 或 `json` |

**响应:** PNG 或 JSON 文件下载

### 解析手动 JSON

解析手动粘贴的 Quack JSON 数据。

```http
POST /api/quack/parse-manual
Content-Type: application/json

{
  "json_data": { /* Quack 原始 JSON */ }
}
```

---

## AI 代理

### 聊天代理 (SSE 流式)

代理 AI 聊天请求，支持流式响应。

```http
POST /api/proxy/chat
Content-Type: application/json

{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000,
  "stream": true
}
```

**响应:** Server-Sent Events 流

### 模型列表

获取可用模型列表。

```http
POST /api/proxy/models
Content-Type: application/json

{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx"
}
```

**响应:**
```json
{
  "object": "list",
  "data": [
    {"id": "gpt-4", "object": "model"},
    {"id": "gpt-3.5-turbo", "object": "model"}
  ]
}
```

### 图像生成代理

代理图像生成请求。

```http
POST /api/proxy/image
Content-Type: application/json

{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "prompt": "a cute cat",
  "model": "dall-e-3",
  "size": "1024x1024"
}
```

**响应:**
```json
{
  "created": 1234567890,
  "data": [
    {"url": "https://..."}
  ]
}
```

---

## 错误响应

所有 API 使用统一的错误响应格式:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

### 错误码

| HTTP 状态码 | 错误码 | 说明 |
|-------------|--------|------|
| 400 | `PARSE_ERROR` | 文件解析失败 |
| 400 | `VALIDATION_ERROR` | 数据验证失败 |
| 400 | `QUACK_IMPORT_ERROR` | Quack 导入失败 |
| 401 | `UNAUTHORIZED` | 未授权（API Key 无效） |
| 403 | `URL_NOT_ALLOWED` | 目标 URL 不在白名单 |
| 413 | `FILE_TOO_LARGE` | 文件超过大小限制 |
| 429 | `RATE_LIMITED` | 请求过于频繁 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |
| 502 | `UPSTREAM_ERROR` | 上游服务错误 |
| 504 | `TIMEOUT` | 请求超时 |

---

## 安全说明

### AI 代理白名单

默认允许代理的域名：
- `api.openai.com`
- `api.anthropic.com`
- `openrouter.ai`
- `generativelanguage.googleapis.com`

如需支持本地服务 (Ollama/LM Studio)，需设置环境变量：
```bash
CARDFORGE_PROXY_ALLOW_LOCALHOST=true
```

### 速率限制

代理接口默认限制：每个 IP 每 60 秒最多 10 次请求。

可通过环境变量调整：
```bash
CARDFORGE_RATE_LIMIT_REQUESTS=20
CARDFORGE_RATE_LIMIT_WINDOW_SECONDS=60
```

---

## multipart 字段名规范

所有上传接口统一使用 `file` 字段名。
