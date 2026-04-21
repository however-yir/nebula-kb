# 结构化可维护改造记录

## 本轮落地

- 冻结五个域：用户与认证、知识库、检索问答、应用/工作流、文件与连接器。
- 增加公共契约代码：`apps/common/contracts`。
- 增加公共分层基类：`apps/common/services`、`apps/common/repositories`、`apps/common/policies`。
- 为核心域补齐 `services` / `repositories` / `policies` 包。
- 拆分 `apps/users/serializers/user.py`：
  - 账号找回、邮件验证码、语言切换移入 `apps/users/serializers/account.py`。
  - 用户角色和默认资源权限移入 `apps/users/services/user_permission_service.py`。
  - 原导入路径继续兼容。

## 下一步优先级

1. 拆 `apps/knowledge/serializers/document.py`，先把导入/导出、标签、批处理拆到独立 serializer。
2. 拆 `apps/knowledge/views/document.py`，保留 `DocumentView.*` 旧路由引用。
3. 拆 `apps/application/serializers/application.py`，把应用导入导出、工作流发布、知识库映射分离。
4. 给登录、工作空间、知识库列表、应用列表补接口级回归用例。

