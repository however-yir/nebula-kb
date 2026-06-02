# NebulaKB API 契约

当前契约版本：`2026-04-21`

## API v1

公开稳定接口统一挂在 `/api/v1`。v1 面向外部集成和端到端验收，覆盖登录、知识库创建、文档上传、问答检索、反馈提交、应用发布和资源授权。

机器可解析 OpenAPI 描述见 [`docs/api/openapi-v1.json`](./openapi-v1.json)，当前 OpenAPI 版本为 `3.1.0`。

核心端点：

| operationId | 方法 | 路径 | 鉴权 |
| --- | --- | --- | --- |
| `auth.login` | `POST` | `/api/v1/auth/login` | 无 |
| `knowledge_base.create` | `POST` | `/api/v1/knowledge-bases` | Bearer |
| `document.upload` | `POST` | `/api/v1/knowledge-bases/{knowledge_base_id}/documents` | Bearer |
| `question.ask` | `POST` | `/api/v1/knowledge-bases/{knowledge_base_id}/ask` | Bearer |
| `feedback.submit` | `POST` | `/api/v1/feedback` | Bearer |
| `application.publish` | `POST` | `/api/v1/applications/{application_id}/versions` | Bearer |
| `permission.resource_grant` | `POST` | `/api/v1/permissions/resources` | Bearer |

端到端主路径必须至少覆盖：

```text
login -> create_knowledge_base -> upload_document -> parse_document -> ask_with_retrieval -> submit_feedback
```

## 鉴权

用户、工作空间和后台管理 API 使用：

```http
Authorization: Bearer <token>
```

已发布应用可使用范围受限的应用密钥：

```http
X-API-Key: <application_api_key>
```

API Key 必须绑定应用、权限范围和过期时间；启停、轮换和删除必须进入审计日志，敏感字段在日志和错误里只允许输出脱敏值。

## 响应包络

所有 JSON API 返回统一结构：

```json
{
  "code": 200,
  "message": "Success",
  "data": {}
}
```

分页 `data` 固定为：

```json
{
  "total": 0,
  "records": [],
  "current": 1,
  "size": 20
}
```

## 错误码

| 范围 | 用途 |
| --- | --- |
| `200-299` | 成功 |
| `400-499` | HTTP/客户端语义错误 |
| `500-599` | 服务端或兼容旧错误 |
| `1000-1099` | 用户与认证 |
| `3000-4999` | 业务域错误 |
| `5000-5999` | 校验/导入/迁移类错误 |

新增错误码要先登记到契约文档或对应域的 API 文档，再实现。

错误响应仍使用统一包络：

```json
{
  "code": 1001,
  "message": "Unauthorized",
  "data": {
    "request_id": "req_123",
    "field": "authorization"
  }
}
```

## OpenAPI 维护规则

- `docs/api/openapi-v1.json` 是 v1 外部契约的最小稳定描述。
- 新增 v1 endpoint 时，必须同时补充 `operationId`、鉴权、成功响应、错误响应和分页参数。
- 破坏性字段变更必须新增路径版本，不得直接改动 v1 语义。
- `scripts/quality-gate.sh api-security-release` 会检查 OpenAPI、鉴权、分页和错误码关键字段是否漂移。

## 查询参数

- 分页：继续兼容路径参数 `current_page`、`page_size`。
- 排序：统一使用 `order_by`，降序使用 `-field_name`。
- 筛选：显式 query 参数优先，避免新增 opaque filter JSON。
- 字段命名：前后端统一 `snake_case`；历史字段保留兼容，新增字段不得混用 `camelCase`。

## 版本策略

现有 API 保持 v2 稳定。破坏性变更必须新增路径版本或新 endpoint，旧 endpoint 进入兼容期后再删除。

## 开发门禁

任何新增或变更 API，在开发前必须完成：

- 契约字段、错误码、分页、排序/筛选、版本策略确认。
- 前端调用方确认字段命名和空值语义。
- 最小回归路径：登录、工作空间、知识库、应用管理至少不被破坏。

Batch 8 发布验收脚本：

```bash
bash scripts/quality-gate.sh api-security-release
```
