# YourRAG — 统一 RAG 工具包 | Unified RAG Toolkit

[![CI](https://github.com/however-yir/yourrag/actions/workflows/tests.yml/badge.svg)](https://github.com/however-yir/yourrag/actions/workflows/tests.yml)
[![Docs](https://img.shields.io/badge/docs-deployment-0A7EFA)](https://github.com/however-yir/yourrag/tree/main/docs)
[![License](https://img.shields.io/badge/license-Apache--2.0-16A34A)](./LICENSE)
[![Status](https://img.shields.io/badge/status-active-2563EB)](https://github.com/however-yir/yourrag)

> **非官方声明（Non-Affiliation）**
> 本仓库为社区维护的衍生/二次开发版本，与上游项目及其权利主体不存在官方关联、授权背书或从属关系。
> **商标声明（Trademark Notice）**
> 相关项目名称、Logo 与商标归其各自权利人所有。本仓库仅用于说明兼容/来源，不主张任何商标权利。

![YourRAG Logo](./assets/yourrag-logo.svg)

**YourRAG** 融合三个 RAG 方向项目的精华，统一为一个 Python RAG 工具包：

| 原项目 | 定位 | 合并内容 |
|--------|------|----------|
| `springboot-llm-rag-agent-demo` | Demo / 快速体验 | Ollama-first 配置、断路器工具执行器、SSE 流式对话、ReAct Agent |
| `rag-agent-production-starter` | 生产级起步模板 | JWT/RBAC 认证、限流、审计日志、SQLite/Redis 队列、OpenTelemetry |
| `yourrag` (RAGFlow fork) | 私有化部署引擎 | DeepDoc、Canvas Agent、GraphRAG、多向量存储、MCP、SDK（保持为核心引擎） |

## 架构总览

```
┌───────────────────────────────────────────────────────┐
│        YourRAG Gateway (FastAPI, :9382)               │
│                                                       │
│  /api/v1/health       → 健康检查                      │
│  /api/v1/auth/*       → JWT/RBAC + API Key            │
│  /api/v1/tools        → 工具注册表 (20+ 工具)          │
│  /api/v1/rag/search   → 统一 RAG 检索                  │
│  /api/v1/documents    → 文档上传/摄入                   │
│  /api/v1/agent/*      → ReAct / Canvas 双模式 Agent    │
│  /api/v1/metrics      → Prometheus + JSON 指标         │
│                                                       │
│  中间件: CORS · 请求上下文 · 限流 · 审计               │
└───────────────────┬───────────────────────────────────┘
                    │ 委托
┌───────────────────┴───────────────────────────────────┐
│         YourRAG Engine (Quart, :9380)                  │
│                                                       │
│  知识库 · 文档 · 分块 · Canvas 画布                    │
│  DeepDoc (OCR + 布局 + 13 种文档解析器)                 │
│  GraphRAG · RAPTOR · 高级 RAG                          │
│  MCP Server/Client · 记忆模块 · 25+ 数据源连接器       │
│  多租户 · 加密存储 · OAuth/SSO                         │
│  Python SDK (ragflow_sdk)                              │
└───────────────────────────────────────────────────────┘
```

## 三种运行模式

### 🌱 Demo 模式 — 零外部依赖，本地体验

```bash
export YOURRAG_LLM_PROVIDER=ollama
export YOURRAG_VECTOR_STORE_BACKEND=chroma
export YOURRAG_AGENT_MODE=react
export YOURRAG_SECURITY_ENABLED=false
uv run python -m yourrag_gateway.main
```

### 🏗️ Production 模式 — 生产级起步

```bash
export YOURRAG_LLM_PROVIDER=openai
export YOURRAG_VECTOR_STORE_BACKEND=pinecone
export YOURRAG_SECURITY_ENABLED=true
export YOURRAG_INGESTION_QUEUE_BACKEND=redis
export YOURRAG_REDIS_URL=redis://localhost:6379
uv run python -m yourrag_gateway.main
```

### 🏭 Private 模式 — 企业私有化部署

```bash
export YOURRAG_LLM_PROVIDER=litellm
export YOURRAG_VECTOR_STORE_BACKEND=elasticsearch
export YOURRAG_AGENT_MODE=canvas
export YOURRAG_CRYPTO_ENABLED=true
# 启动 Gateway + Engine 双进程
uv run python -m yourrag_gateway.main &   # FastAPI :9382
uv run python api/apps.py                 # Quart   :9380
```

## 功能全景

### 核心引擎（来自 RAGFlow 深度改造）

| 能力 | 说明 |
|------|------|
| **DeepDoc** | OCR + 布局识别 + 表格提取 + 视觉 LLM，支持 PDF/DOCX/PPTX/Excel/HTML/MD/EPUB/JSON/图片/音频 等 13+ 格式 |
| **Canvas Agent** | 可视化 DSL 图引擎，20+ 组件类型，任意 DAG 拓扑 |
| **GraphRAG** | 实体抽取 + 社区检测 + 知识图谱检索 |
| **RAPTOR** | 文档层次聚类，多粒度检索 |
| **多向量存储** | Elasticsearch / Infinity / OceanBase / OpenSearch，配置切换 |
| **多 LLM** | LiteLLM 支持 40+ 供应商，按模型独立配置 |
| **MCP 协议** | 完整 MCP Server + Client |
| **Python SDK** | `ragflow_sdk`：DataSet / Document / Chunk / Chat / Agent / Memory |
| **25+ 数据源** | SharePoint / Google Drive / Jira / Slack / GitHub / Dropbox / Discord 等 |
| **20+ 工具** | Tavily / Google / DuckDuckGo / arXiv / PubMed / GitHub / SQL / Email / Finance 等 |
| **多租户** | 租户隔离，按租户配置 LLM/模型 |
| **OAuth/SSO** | GitHub / OIDC / 飞书 / 自定义 OAuth |
| **加密存储** | AES-256-CBC 可选，密钥轮换 |

### 生产级加固（来自 Production Starter）

| 能力 | 说明 |
|------|------|
| **JWT/RBAC 认证** | HS256 JWT + 角色/权限模型 + API Key |
| **限流** | 内存 + Redis 双后端，按端点/分钟 |
| **审计日志** | who/what/when/ip 全链路记录 |
| **摄入队列** | SQLite/Redis 可插拔，带重试 + 死信 |
| **后台 Worker** | 线程式队列消费者，可配置轮询间隔 |
| **OpenTelemetry** | Traces + Logs 全栈，OTLP 导出 |
| **Prometheus** | HTTP/RAG/Ingestion 多维度指标 |
| **请求上下文** | request_id/trace_id/session_id 跨层传播 |

### 开发者体验（来自 Demo）

| 能力 | 说明 |
|------|------|
| **Ollama-first** | 全本地运行，零云服务依赖 |
| **断路器** | 工具执行器 + 失败追踪 + 冷却降级 |
| **SSE 流式** | Token 级实时流式对话 |
| **Chroma 本地** | 最简向量数据库，开箱即用 |
| **ReAct Agent** | 手工构建 LangGraph StateGraph + 降级回退 |
| **Mock 模式** | `use_mock_services=true` 零依赖测试 |

## 快速启动

### Docker Compose（全栈，推荐）

```bash
cd docker
cp .env.example .env.local
# 编辑 .env.local 修改密码与管理员账号
docker compose --env-file .env.local -f docker-compose.yml up -d
curl -f http://127.0.0.1:9380/v1/system/ping  # Engine
curl -f http://127.0.0.1:9382/api/v1/health   # Gateway
```

轻量开发档位：

```bash
cd docker
cp .env.local.lite.example .env.local.lite
docker compose --env-file .env.local.lite -f docker-compose.yml up -d
```

### 从源码

```bash
git clone https://github.com/however-yir/yourrag.git
cd yourrag
uv sync
cp .env.example .env
# 编辑 .env 选择运行模式和配置

# 启动 Gateway
uv run python -m yourrag_gateway.main

# (可选) 启动 Engine — 获取 Canvas/DeepDoc/GraphRAG 等完整能力
uv run python api/apps.py
```

## API 速查

### Gateway 路由 (`:9382`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/auth/login` | JWT 登录 |
| GET | `/api/v1/auth/me` | 当前用户信息 |
| POST | `/api/v1/auth/api-keys` | 创建 API Key |
| GET | `/api/v1/tools` | 工具注册表 |
| POST | `/api/v1/rag/search` | RAG 检索 |
| POST | `/api/v1/documents/upload` | 文档上传 |
| POST | `/api/v1/agent/chat` | Agent 对话 |
| POST | `/api/v1/agent/chat/stream` | SSE 流式对话 |
| GET | `/api/v1/metrics` | JSON 指标 |
| GET | `/api/v1/metrics/prometheus` | Prometheus 指标 |

### Engine 路由 (`:9380`)

完整 RESTful API — 知识库/文档/分块/画布/LLM/对话/搜索/数据集/记忆/连接器/MCP/评估 等。

## 配置

所有配置通过环境变量驱动（前缀 `YOURRAG_`），详见 [.env.example](./.env.example)。

核心配置项：

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `YOURRAG_LLM_PROVIDER` | `litellm` | LLM 供应商：ollama / openai / litellm |
| `YOURRAG_VECTOR_STORE_BACKEND` | `elasticsearch` | 向量存储：chroma / sqlite / pinecone / elasticsearch / infinity / oceanbase / opensearch |
| `YOURRAG_AGENT_MODE` | `canvas` | Agent 模式：react / canvas |
| `YOURRAG_SECURITY_ENABLED` | `true` | 是否启用 JWT 认证 |
| `YOURRAG_INGESTION_QUEUE_BACKEND` | `sqlite` | 摄入队列：sqlite / redis |

Engine 层配置：
- `conf/service_conf.yaml` — 服务级默认配置
- `tools/scripts/generate_rsa_keys.sh` — RSA 密钥初始化

## 项目结构

```
yourrag/
├── yourrag_gateway/          ← 统一 FastAPI 网关层
│   ├── main.py               ← 应用入口
│   ├── core/                 ← 配置 · 日志 · 请求上下文
│   ├── auth/                 ← JWT/RBAC 认证
│   ├── security/             ← 限流
│   ├── audit/                ← 审计日志
│   ├── observability/        ← Prometheus + OpenTelemetry
│   ├── queue/                ← SQLite/Redis 队列
│   ├── tools/                ← 断路器工具执行器
│   ├── middleware/           ← 请求上下文中间件
│   ├── agent/react/          ← ReAct Agent
│   └── api/                  ← 路由 · Schema · 依赖注入
│
├── api/                      ← Engine: Quart API 引擎
├── rag/                      ← Engine: RAG 核心引擎
├── agent/                    ← Engine: Canvas Agent + 20+ 工具
├── memory/                   ← Engine: 向量记忆模块
├── common/                   ← Engine: 公共工具
├── deepdoc/                  ← Engine: 文档解析引擎
├── mcp/                      ← Engine: MCP 协议
├── sdk/                      ← Engine: Python SDK
├── conf/                     ← YAML 配置
├── docker/                   ← Docker 部署
├── docs/                     ← 文档
├── test/                     ← 测试
├── .env.example              ← 统一配置模板
└── MERGE.md                  ← 合并说明文档
```

## 企业级加固

已完成 50+ 项企业级完善 + Gateway 层生产级特性：

- 🔒 安全：CORS 白名单 · 默认密码守卫 · SECRET_KEY 轮换 · Pickle 反序列化修复 · ES TLS · JWT/RBAC · 限流 · 审计
- 📊 可观测：Prometheus · Grafana 仪表盘 · OpenTelemetry 全栈 · Langfuse LLM 观测
- 💾 存储：Redis AOF · ES ILM 策略 · 自动备份 · 冷数据归档
- 🔄 CI/CD：Codecov · Go/Python/Frontend 检查 · 多架构构建 · SBOM · Dependabot
- ⚙️ 架构：LLM 缓存 · 配置热重载 · Nginx 增强 · 摄入队列 · 断路器

完整清单见：[docs/customization/completed-checklist.md](docs/customization/completed-checklist.md)

## 部署文档

- [单机部署](docs/deployment/single-host.md)
- [Docker Compose](docs/deployment/docker-compose.md)
- [Kubernetes/Helm](docs/deployment/kubernetes.md)

## 评测与观测路径

| 层面 | 入口 | 用途 |
|------|------|------|
| 健康探针 | `curl /v1/system/ping` | 最小可用性检查 |
| 快速上手 | `docs/quickstart.mdx` | 新成员最短路径 |
| 部署说明 | `docs/deployment/*` | 三套部署面 |
| 发布记录 | `docs/release_notes.md` | 版本变化 |
| Helm 部署 | `helm/README.md` | K8s 安装入口 |
| 配置基线 | `conf/service_conf.yaml` | 服务默认配置 |
| 合并说明 | `MERGE.md` | 三项目合并文档 |

## 与上游关系

- 本项目基于上游 RAGFlow 进行二次开发。
- 继续遵循 Apache-2.0（见 `LICENSE`）。
- 归属与附加说明见 `NOTICE` 与 `LICENSE-ADDITIONAL.md`。

## Engineering Quality

- Quality plan: [docs/ENGINEERING_QUALITY.md](docs/ENGINEERING_QUALITY.md)
- Contract tests: [tests/repo_contract_test.sh](tests/repo_contract_test.sh)
- Contract CI: [.github/workflows/repo-contract-ci.yml](.github/workflows/repo-contract-ci.yml)

```bash
bash tests/repo_contract_test.sh
```

---

Series: [local-ai-hub](https://github.com/however-yir/local-ai-hub) · [LZKB](https://github.com/however-yir/LZKB) · **YourRAG**
