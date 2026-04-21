# LZKB 模块边界冻结

本轮目标是结构化可维护，不重写业务。模块边界先冻结，后续改造只允许在明确归属内演进，跨域调用通过 services / repositories / policies 进入。

## 冻结域

| 域 | 归属目录 | API 根路径 | 边界说明 |
| --- | --- | --- | --- |
| 用户与认证 | `apps/users`, `apps/common/auth` | `user/*`, `user_manage/*`, `workspace/<workspace_id>/user*` | 登录、Token、用户资料、用户管理、用户角色绑定。 |
| 知识库 | `apps/knowledge` | `workspace/<workspace_id>/knowledge/*` | 知识库、文档、分段、问题、标签、知识库工作流版本。 |
| 检索问答 | `apps/chat`, `apps/application/chat_pipeline` | `chat_message/*`, `chat/*`, `historical_conversation/*` | 会话、检索问答、嵌入聊天、投票、历史会话。 |
| 应用/工作流 | `apps/application`, `apps/trigger` | `workspace/<workspace_id>/application/*`, `workspace/<workspace_id>/trigger/*` | 应用配置、工作流编排、版本、触发器、统计。 |
| 文件与连接器 | `apps/oss`, `apps/tools`, `apps/models_provider`, `apps/local_model` | `oss/file`, `workspace/<workspace_id>/tool/*`, `workspace/<workspace_id>/model/*` | 文件上传/下载、工具连接器、模型供应商、本地模型调用。 |

## 分层约定

所有域按 `views -> serializers -> services -> repositories -> policies` 维护：

- `views`: HTTP 入参、权限装饰器、响应包装，不写业务事务。
- `serializers`: 请求/响应结构、字段校验、兼容旧调用；迁移期允许代理到 service。
- `services`: 业务用例、事务编排、跨 repository 协调。
- `repositories`: ORM/SQL/外部客户端访问，不返回 HTTP 响应。
- `policies`: 授权、所有权、资源可见性、业务准入规则。

## 渐进规则

- 旧入口保持兼容，先移动内部逻辑，再改调用方。
- 超过 800 行的文件按域优先拆分；每次拆分必须保留最小回归路径。
- 新 API 先补契约和前后端确认，再写 view/serializer/service。
- 跨域访问不得直接穿透到对方 model 细节；先在所属域沉淀 service/repository。

