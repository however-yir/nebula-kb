# LZKB 一期企业能力边界

本文定义 LZKB 一期企业交付的最小可售卖边界。验收目标是：权限可控、行为可追溯、数据可隔离、客户可交付。

## 能力范围

一期纳入以下能力：

| 能力 | 一期边界 | 交付状态 |
| --- | --- | --- |
| 工作空间 | 以 `workspace_id` 作为租户隔离边界，应用、知识库、模型、工具、API Key、审计日志和运营指标均归属工作空间 | 已固化 |
| RBAC | 使用平台角色、工作空间角色和资源授权组合控制操作范围 | 已固化 |
| 审计日志 | 所有接入 `@log` 的操作写入统一事件契约，字段为 `event_name`、`actor`、`resource`、`timestamp`、`result` | 已固化 |
| SSO | 一期作为交付边界和账号来源契约；原生 OIDC/SAML 可按客户 IdP 单独扩展，必须写入登录审计 | 边界定义 |
| API Key | 应用 API Key 绑定工作空间和应用，支持启停、过期、跨域白名单 | 已有并纳入手册 |
| 配额限流 | 对话访问次数和 API Key 调用纳入工作空间治理；超限必须返回明确错误并写入审计 | 边界定义 |
| 基础可观测性 | 工作空间运营指标覆盖调用量、成本、活跃度、失败率 | 已新增接口 |

## 角色模型

| 角色 | 内部映射 | 能力边界 |
| --- | --- | --- |
| 平台管理员 | `ADMIN` | 管理全局配置、工作空间、用户、角色、审计、资源授权和模型配置 |
| 工作空间管理员 | `WORKSPACE_MANAGE:/WORKSPACE/{workspace_id}` | 管理指定工作空间内成员、资源、API Key、运营指标和资源授权 |
| 成员 | `USER:/WORKSPACE/{workspace_id}` | 使用被授权的应用、知识库、模型和工具；可按资源权限创建或编辑 |
| 只读 | 资源权限 `VIEW` | 只能查看被授权资源、对话记录和统计，不得创建、修改、删除或导出敏感配置 |
| 服务账号 | 应用 API Key | 无交互式登录能力，仅可调用绑定应用的 API；必须配置负责人、过期时间、配额和轮换周期 |

## 审计事件契约

每条审计事件必须包含：

```json
{
  "event_name": "application.create_an_application",
  "actor": {
    "type": "user",
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "roles": ["ADMIN"]
  },
  "resource": {
    "workspace_id": "default",
    "path": "/admin/api/workspace/default/application",
    "method": "POST",
    "object": {"name": "知识助手"}
  },
  "timestamp": "2026-04-21T10:00:00+08:00",
  "result": {
    "status": 200,
    "success": true
  }
}
```

事件覆盖范围：

| 类型 | 示例 |
| --- | --- |
| 登录 | 登录、登出、登录失败、账号禁用或锁定 |
| 管理操作 | 用户、角色、工作空间、资源授权、API Key、模型和系统设置变更 |
| 数据访问 | 应用、知识库、对话记录、审计日志、运营指标查询 |
| 配置变更 | 邮件设置、登录认证、显示设置、访问控制、跨域和令牌配置 |

## 租户隔离与资源归属

1. 所有租户内资源必须持有 `workspace_id`，默认值仅用于单租户或开发环境。
2. API 路径中的 `workspace_id` 必须与资源表中的 `workspace_id` 一致。
3. 跨工作空间访问必须被拒绝；共享资源只能通过显式共享或资源映射读取。
4. 审计日志按 `workspace_id` 写入，平台管理员可跨工作空间查询，工作空间管理员只能查询本工作空间。
5. API Key 归属于应用，应用归属于工作空间，因此 API Key 不得跨工作空间复用。

## 运营指标

新增工作空间指标接口：

```http
GET /admin/api/workspace/{workspace_id}/operation_metrics?start_time=2026-04-01&end_time=2026-04-21
```

返回字段：

| 字段 | 含义 |
| --- | --- |
| `call_count` | 时间范围内对话调用量 |
| `total_cost` | 时间范围内模型调用成本累计，沿用现有 `ChatRecord.const` 计费单位 |
| `active_user_count` | 时间范围内活跃对话用户数 |
| `operation_count` | 时间范围内审计操作数 |
| `failed_operation_count` | 审计状态码大于等于 400 的失败操作数 |
| `failure_rate` | `failed_operation_count / operation_count` |
| `last_activity_at` | 最近一次对话活动时间 |

审计查询接口：

```http
GET /admin/api/workspace/{workspace_id}/audit_log/{current_page}/{page_size}
```

可选过滤：`event_name`、`actor_id`、`result=success|failure`、`start_time`、`end_time`。
