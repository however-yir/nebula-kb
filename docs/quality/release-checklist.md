# LZKB Release Checklist

每次发布前使用这份清单。未完成项必须记录负责人、风险等级和是否允许发布。

## 1. 基础准备

- [ ] 当前分支已同步主分支，迁移文件无冲突。
- [ ] `.env.example`、`config_example.yml` 与新增配置保持一致。
- [ ] 没有提交真实密码、API Key、token、数据库连接串。
- [ ] 依赖变更已通过依赖审计或记录风险豁免。

## 2. 固定质量门禁

```bash
bash scripts/quality-gate.sh smoke
bash scripts/quality-gate.sh api
bash scripts/quality-gate.sh auth
bash scripts/quality-gate.sh permission
COVERAGE_FAIL_UNDER=50 bash scripts/quality-gate.sh coverage
```

- [ ] smoke 通过。
- [ ] API regression 通过。
- [ ] auth/token 回归通过。
- [ ] permission/越权回归通过。
- [ ] 覆盖率不低于当前阶段门槛。

## 3. 最小验收闭环

- [ ] 登录：成功登录、失败登录、退出、token 失效。
- [ ] 知识库：创建/读取/删除受权限控制。
- [ ] 上传：合法文件成功，非法文件拒绝，解析任务状态可见。
- [ ] 检索：限定在授权知识库内，空结果可解释。
- [ ] 应用：绑定知识库并完成一次默认工作流执行。
- [ ] 权限：普通用户不能访问未授权 workspace/resource。
- [ ] API Key：创建、禁用、过期、撤销和公开接口调用验证完成。

## 4. 非功能检查

- [ ] 并发压测：登录、上传、检索、公开接口无异常错误率。
- [ ] 大文件：边界文件可控，超限文件错误明确。
- [ ] 长文本：切片、token 估算、模型调用边界稳定。
- [ ] 异步队列：积压任务可观察、可恢复、可重试。
- [ ] 越权攻击：伪造 token/API Key、跨 workspace/resource ID 均被拒绝。

## 5. Rollback

- [ ] 镜像或包版本可回退。
- [ ] 数据库迁移有回滚说明；不可逆迁移已标记并备份。
- [ ] 配置变更可恢复到上一版本。
- [ ] 发布监控指标明确：错误率、p95 延迟、队列积压、登录失败率、公开接口 401/403 比例。

## 6. 发布结论

- [ ] 可发布。
- [ ] 有条件发布，风险已登记。
- [ ] 不可发布，存在 P0/P1 阻断问题。
