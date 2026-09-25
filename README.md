# SAG MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-orange.svg)](https://modelcontextprotocol.io)
[![M8ven Score](https://m8ven.ai/badge/mcp/guazixiong-sag-mcp-server-1eicq0?v=221a3722c3a0755ad59d3fd94fcbc9f1)](https://m8ven.ai/mcp/guazixiong-sag-mcp-server-1eicq0)

[English](#features) | [中文](#中文文档)

Full read/write MCP server for [SAG](https://github.com/Zleap-AI/SAG) knowledge base. Exposes 18 tools over Streamable HTTP transport — compatible with Claude Desktop, Cursor, VS Code, and any MCP client.

---

## Features

- **18 tools**: source/document CRUD, semantic search, knowledge graph queries, model config
- **Streamable HTTP**: connect from any MCP client without local dependencies
- **Bearer auth**: JWT token authentication built-in
- **Zero config**: works with a running SAG instance out of the box

## Quick Start

### 1. Prerequisites

A running SAG instance (Docker or native). See [SAG deployment guide](https://github.com/Zleap-AI/SAG#readme).

### 2. Install

```bash
pip install sag-mcp-server
```

Or from source:

```bash
git clone https://github.com/Zleap-AI/sag-mcp-server.git
cd sag-mcp-server
pip install -e .
```

### 3. Run

**HTTP mode** (recommended):

```bash
export SAG_API_URL=http://your-sag-host:9002
sag-mcp-server http 9003
```

**stdio mode** (for local integration):

```bash
sag-mcp-server stdio
```

### 4. Connect from Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": {
        "Authorization": "Bearer <your-jwt-token>"
      }
    }
  }
}
```

Get a token:

```bash
curl -s -X POST http://your-sag-host:9002/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"name":"Admin"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
```

## Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Sources** | `list_sources` | List all knowledge base sources |
| | `create_source` | Create a new source |
| | `delete_source` | Delete a source and all its data |
| **Documents** | `list_documents` | List documents in a source |
| | `upload_document` | Upload a local file (auto-parses + extracts) |
| | `ingest_text` | Write text directly (no file needed) |
| | `reprocess_document` | Re-process a document |
| | `pause_document` | Pause processing |
| | `resume_document` | Resume processing |
| | `delete_document` | Delete a document |
| **Retrieval** | `search` | Semantic search with LLM summary |
| | `get_entity` | Query knowledge graph entity |
| | `outline` | Get document outline |
| | `grep` | Keyword/regex search |
| | `read_document` | Read full document text |
| **Config** | `get_model_config` | View model configuration |
| | `update_model_config` | Update model settings |
| | `test_model_config` | Test model connectivity |

## Configuration

All configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SAG_API_URL` | `http://localhost:9002` | SAG API base URL |
| `SAG_TOKEN` | (empty = auto-login) | JWT Bearer token |
| `SAG_LOGIN_NAME` | `Admin` | Login username (when token is empty) |
| `SAG_MCP_PORT` | `9003` | HTTP server port |

## Client Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

### Dify

- Type: **Streamable HTTP**
- URL: `http://your-sag-host:9003/mcp/`
- Header: `Authorization: Bearer <token>`

## Docker

Run as a container alongside SAG:

```yaml
# docker-compose.yml addition
services:
  mcp:
    build: .
    environment:
      SAG_API_URL: http://api:8000
      SAG_SECRET_KEY: ${SAG_SECRET_KEY}
    ports:
      - "9003:9003"
    command: ["sag-mcp-server", "http", "9003"]
    depends_on:
      api:
        condition: service_healthy
```

## Development

```bash
git clone https://github.com/Zleap-AI/sag-mcp-server.git
cd sag-mcp-server
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

## API Compatibility

Requires SAG v0.7.x+ with the following endpoints:

- `POST /api/v1/auth/login` — JWT authentication
- `GET/POST/DELETE /api/v1/sources` — Source CRUD
- `GET/POST/DELETE /api/v1/sources/{id}/documents` — Document CRUD
- `POST /api/v1/search` — Semantic search
- `GET /api/v1/system/model-config` — Model configuration

## License

MIT License. See [LICENSE](LICENSE) for details.

---

# 中文文档

[English](#features) | [中文](#中文文档)

基于 [SAG](https://github.com/Zleap-AI/SAG) 知识库的读写 MCP Server。通过 Streamable HTTP 暴露 18 个工具，兼容 Claude Desktop、Cursor、VS Code 及所有 MCP 客户端。

---

## 特性

- **18 个工具**：信源/文档增删改查、语义检索、知识图谱查询、模型配置
- **Streamable HTTP**：无需本地安装任何依赖，客户端通过 HTTP 直连
- **Bearer 鉴权**：内置 JWT token 认证
- **零配置**：与运行中的 SAG 实例直接配合使用

## 快速开始

### 1. 前提条件

运行中的 SAG 实例（Docker 或原生部署）。参见 [SAG 部署指南](https://github.com/Zleap-AI/SAG#readme)。

### 2. 安装

```bash
pip install sag-mcp-server
```

或从源码安装：

```bash
git clone https://github.com/Zleap-AI/sag-mcp-server.git
cd sag-mcp-server
pip install -e .
```

### 3. 启动

**HTTP 模式**（推荐）：

```bash
export SAG_API_URL=http://your-sag-host:9002
sag-mcp-server http 9003
```

**stdio 模式**（本地集成）：

```bash
sag-mcp-server stdio
```

### 4. 连接 Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": {
        "Authorization": "Bearer <your-jwt-token>"
      }
    }
  }
}
```

获取 token：

```bash
curl -s -X POST http://your-sag-host:9002/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"name":"Admin"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
```

## 工具清单

| 类别 | 工具 | 说明 |
|------|------|------|
| **信源** | `list_sources` | 列出所有知识库信源 |
| | `create_source` | 创建新信源 |
| | `delete_source` | 删除信源及全部数据 |
| **文档** | `list_documents` | 列出信源下文档 |
| | `upload_document` | 上传本地文件（自动解析+抽取） |
| | `ingest_text` | 直接写入文本（无需文件） |
| | `reprocess_document` | 重新处理文档 |
| | `pause_document` | 暂停处理 |
| | `resume_document` | 恢复处理 |
| | `delete_document` | 删除文档 |
| **检索** | `search` | 语义检索（含 LLM 摘要） |
| | `get_entity` | 查询知识图谱实体 |
| | `outline` | 获取文档大纲 |
| | `grep` | 关键词/正则检索 |
| | `read_document` | 读取文档全文 |
| **模型** | `get_model_config` | 查看模型配置 |
| | `update_model_config` | 更新模型设置 |
| | `test_model_config` | 测试模型连通性 |

## 配置说明

所有配置通过环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SAG_API_URL` | `http://localhost:9002` | SAG API 地址 |
| `SAG_TOKEN` | （空=自动登录） | JWT Bearer token |
| `SAG_LOGIN_NAME` | `Admin` | 登录用户名（token 为空时生效） |
| `SAG_MCP_PORT` | `9003` | HTTP 服务端口 |

## 客户端配置

### Claude Desktop

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "sag": {
      "type": "http",
      "url": "http://your-sag-host:9003/mcp/",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

### Dify

- 类型：**Streamable HTTP**
- URL：`http://your-sag-host:9003/mcp/`
- 请求头：`Authorization: Bearer <token>`

## Docker 部署

与 SAG 一起以容器方式运行：

```yaml
# 添加到 docker-compose.yml
services:
  mcp:
    build: .
    environment:
      SAG_API_URL: http://api:8000
      SAG_SECRET_KEY: ${SAG_SECRET_KEY}
    ports:
      - "9003:9003"
    command: ["sag-mcp-server", "http", "9003"]
    depends_on:
      api:
        condition: service_healthy
```

## 开发指南

```bash
git clone https://github.com/Zleap-AI/sag-mcp-server.git
cd sag-mcp-server
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/
```

## API 兼容性

需要 SAG v0.7.x+，支持以下接口：

- `POST /api/v1/auth/login` — JWT 认证
- `GET/POST/DELETE /api/v1/sources` — 信源增删改查
- `GET/POST/DELETE /api/v1/sources/{id}/documents` — 文档增删改查
- `POST /api/v1/search` — 语义检索
- `GET /api/v1/system/model-config` — 模型配置

## 许可证

MIT License。详见 [LICENSE](LICENSE)。
