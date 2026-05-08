# YourRAG — 三项目合并说明书

## 合并概览

| 原项目 | 定位 | 合并策略 |
|--------|------|----------|
| **springboot-llm-rag-agent-demo** (P1) | 校园/企业 Demo | SSE 流式、断路器工具执行器、Ollama-first 模式 → 融入 `yourrag_gateway/tools/` + `agent/react/` |
| **rag-agent-production-starter** (P2) | 生产级起步模板 | JWT/RBAC 认证、限流、审计、队列、OTEL → 融入 `yourrag_gateway/auth/` + `security/` + `audit/` + `queue/` + `observability/` |
| **yourrag** (P3) | 私有化部署引擎 (RAGFlow fork) | **保持不动**，作为核心引擎继续运行于 `:9380` |

## 合并后的架构

```
┌───────────────────────────────────────────────────┐
│          YourRAG Gateway (FastAPI, :9382)         │
│                                                   │
│  /api/v1/health     → Health check               │
│  /api/v1/auth/*     → JWT/RBAC + API Key (P2)    │
│  /api/v1/tools      → Tool registry (P1+P3)     │
│  /api/v1/rag/*      → Unified RAG search         │
│  /api/v1/documents  → Document upload            │
│  /api/v1/agent/*    → ReAct (P1) / Canvas (P3)  │
│  /api/v1/metrics    → Prometheus + JSON (P2)     │
│                                                   │
│  Middleware:                                       │
│  • RequestContext (P2: request_id, trace_id)      │
│  • CORS (P3: configurable origins)               │
│  • Rate Limiter (P2: in-memory + Redis)           │
│                                                   │
│  New modules (yourrag_gateway/):                  │
│  • core/settings.py  — Pydantic Settings + YAML   │
│  • auth/             — JWT/RBAC + API Key          │
│  • security/         — Rate Limiting               │
│  • audit/            — Audit logging               │
│  • observability/    — Prometheus + OpenTelemetry  │
│  • queue/            — SQLite/Redis queue backend   │
│  • tools/executor.py — Circuit breaker (P1)        │
│  • agent/react/      — ReAct agent (P1)            │
│  • middleware/       — Request context middleware   │
└───────────────┬───────────────────────────────────┘
                │ delegates to
┌───────────────┴───────────────────────────────────┐
│         YourRAG Engine (Quart, :9380) [P3]        │
│                                                   │
│  /api/v1/kb, dataset, document, chunk, …         │
│  Canvas Agent, DeepDoc, GraphRAG                  │
│  MCP Server/Client, Memory, Connectors           │
│  Multi-tenant, Encryption, OAuth/SSO              │
│  Python SDK (ragflow_sdk)                         │
│                                                   │
│  Core modules: api/, rag/, agent/, memory/,       │
│  common/, deepdoc/, mcp/, sdk/                    │
└───────────────────────────────────────────────────┘
```

## 包结构

```
yourrag/
├── yourrag_gateway/          ← 【新增】统一 FastAPI 网关层
│   ├── __init__.py
│   ├── main.py               ← FastAPI 应用入口
│   ├── core/
│   │   ├── settings.py       ← Pydantic Settings（统一三项目配置）
│   │   ├── logging.py        ← 结构化 JSON 日志
│   │   └── request_context.py ← 请求上下文 (contextvars)
│   ├── auth/
│   │   ├── models.py         ← AuthContext, RBAC
│   │   ├── jwt_utils.py      ← HS256 JWT (无 PyJWT 依赖)
│   │   └── service.py        ← 认证服务 (可对接 P3 DB)
│   ├── security/
│   │   └── rate_limit.py     ← 限流 (内存 + Redis)
│   ├── audit/
│   │   └── service.py        ← 审计日志
│   ├── observability/
│   │   ├── metrics.py        ← Prometheus + 内存指标
│   │   └── telemetry.py      ← OpenTelemetry
│   ├── queue/
│   │   ├── base.py           ← QueueBackend Protocol
│   │   ├── sqlite_queue.py   ← SQLite 队列
│   │   ├── redis_queue.py    ← Redis 队列
│   │   └── factory.py        ← 工厂方法
│   ├── tools/
│   │   └── executor.py       ← 断路器工具执行器 (P1)
│   ├── middleware/
│   │   └── request_context.py ← 请求上下文中间件
│   ├── agent/
│   │   └── react/
│   │       └── service.py    ← ReAct Agent (P1, 桥接 P3)
│   └── api/
│       ├── schemas.py        ← 统一 Pydantic 模型
│       ├── dependencies.py   ← FastAPI 依赖注入
│       └── routes.py         ← 统一路由
│
├── api/                      ← [P3 原有] Quart API 引擎
├── rag/                      ← [P3 原有] RAG 核心引擎
├── agent/                    ← [P3 原有] Canvas Agent + 20+ 工具
├── memory/                   ← [P3 原有] 向量记忆模块
├── common/                   ← [P3 原有] 公共工具
├── deepdoc/                  ← [P3 原有] 文档解析引擎
├── mcp/                      ← [P3 原有] MCP 协议
├── sdk/                      ← [P3 原有] Python SDK
├── conf/                     ← [P3 原有] YAML 配置
├── docker/                   ← [P3 原有] Docker 部署
├── .env.example              ← 【新增】统一配置模板
├── pyproject.toml            ← 【更新】新增 gateway 依赖
└── MERGE.md                  ← 【本文件】
```

## 配置合并策略

| 领域 | P1 方案 | P2 方案 | P3 方案 | 合并后方案 |
|------|---------|---------|---------|-----------|
| 配置 | Pydantic BaseSettings (.env) | Dataclass + os.getenv | YAML + 全局可变模块 | **Pydantic Settings (.env) + YAML 兼容** |
| Web 框架 | FastAPI | FastAPI | Quart | **FastAPI Gateway + Quart Engine** |
| LLM | Ollama (本地) | OpenAI (云端) | LiteLLM (多供应商) | **三模式可选：ollama/openai/litellm** |
| 向量存储 | Chroma | Pinecone/SQLite | ES/Infinity/OB/OS | **七种后端统一抽象** |
| Agent | LangGraph ReAct | LangGraph ReAct | Canvas DSL | **两模式：react/canvas** |
| 认证 | 无 | JWT + RBAC | Session + OAuth | **JWT + RBAC + OAuth** |
| 限流 | 无 | 内存 + Redis | 无 | **内存 + Redis** |
| 审计 | 无 | 结构化审计 | 无 | **审计服务** |
| 队列 | 无 | SQLite/Redis | 无 | **SQLite/Redis** |
| 可观测 | Prometheus/OTEL | Prometheus/OTEL | Langfuse | **Prometheus + OTEL + Langfuse** |

## 快速启动

```bash
# 1. 安装依赖
cd yourrag
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 YOURRAG_LLM_PROVIDER, YOURRAG_VECTOR_STORE_BACKEND 等

# 3. 启动 Gateway (FastAPI, port 9382)
uv run python -m yourrag_gateway.main

# 4. 启动 P3 Engine (Quart, port 9380) — 可选，如需 Canvas/DeepDoc
uv run python api/apps.py

# 5. 或者一键全栈
docker compose -f docker/docker-compose.yml up
```

## API 快速参考

| 方法 | 路径 | 来源 | 描述 |
|------|------|------|------|
| GET | /api/v1/health | P1+P2 | 健康检查 |
| POST | /api/v1/auth/login | P2 | JWT 登录 |
| GET | /api/v1/auth/me | P2 | 当前用户信息 |
| POST | /api/v1/auth/api-keys | P2 | 创建 API Key |
| GET | /api/v1/tools | P1 | 工具列表 |
| POST | /api/v1/rag/search | P1+P3 | RAG 检索 |
| POST | /api/v1/documents/upload | P1+P3 | 文档上传 |
| POST | /api/v1/agent/chat | P1+P3 | Agent 对话 |
| POST | /api/v1/agent/chat/stream | P1 | SSE 流式对话 |
| GET | /api/v1/metrics | P2 | JSON 指标 |
| GET | /api/v1/metrics/prometheus | P2 | Prometheus 指标 |

## 三种运行模式

### 模式 1: Demo / 快速体验 (P1 风格)
```bash
YOURRAG_LLM_PROVIDER=ollama
YOURRAG_VECTOR_STORE_BACKEND=chroma
YOURRAG_AGENT_MODE=react
YOURRAG_SECURITY_ENABLED=false
YOURRAG_USE_MOCK_SERVICES=true
```

### 模式 2: Production Starter (P2 风格)
```bash
YOURRAG_LLM_PROVIDER=openai
YOURRAG_VECTOR_STORE_BACKEND=pinecone
YOURRAG_AGENT_MODE=react
YOURRAG_SECURITY_ENABLED=true
YOURRAG_INGESTION_QUEUE_BACKEND=redis
YOURRAG_REDIS_URL=redis://localhost:6379
```

### 模式 3: Private Deployment (P3 风格)
```bash
YOURRAG_LLM_PROVIDER=litellm
YOURRAG_VECTOR_STORE_BACKEND=elasticsearch
YOURRAG_AGENT_MODE=canvas
YOURRAG_SECURITY_ENABLED=true
YOURRAG_CRYPTO_ENABLED=true
# 同时启动 P3 Engine (Quart) 获得完整功能
```
