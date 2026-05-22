# NebulaKB Knowledge Health Baseline

发布日期：2026-04-29

## Release 目标

建立 NebulaKB 的第一条知识资产运营健康基线，让既有 Django 项目具备可展示、可演示、可验证的知识资产生命周期入口。

## 本次包含

- README 首屏定位：知识资产生命周期平台。
- 与 knowledgeops-agent 的边界说明。
- 四张产品截图资产：运营后台、知识库列表、文档入库、问答反馈。
- Demo 数据：`demo-data/knowledge-sample/`。
- 演示脚本：`docs/demo-script.md` 和 `scripts/demo_lifecycle.py`。
- 业务链路测试：`apps/knowledge/tests.py`。
- 运营指标和可观测文档：`docs/observability.md`。

## 验证命令

```bash
python3 scripts/demo_lifecycle.py
PYTHONPATH=apps DJANGO_SETTINGS_MODULE=nebula.settings.test python3 apps/manage.py test knowledge --noinput
```

## 验证范围

| 范围 | 状态 |
|---|---|
| 文件上传 | 已覆盖 |
| 解析失败 | 已覆盖 |
| 索引成功 | 已覆盖 |
| 权限隔离 | 已覆盖 |
| 检索命中 | 已覆盖 |
| 引用返回 | 已覆盖 |
| 空结果兜底 | 已覆盖 |
| 反馈记录 | 已覆盖 |
| 低质答案回看 | 已覆盖 |
| 运营指标快照 | 已覆盖 |

## 截图资产

- `docs/assets/screenshots/admin-dashboard.svg`
- `docs/assets/screenshots/knowledge-health-dashboard.svg`
- `docs/assets/screenshots/knowledge-base-list.svg`
- `docs/assets/screenshots/document-ingestion.svg`
- `docs/assets/screenshots/qa-feedback.svg`

## Demo 数据

- `demo-data/knowledge-sample/01-import-governance.md`
- `demo-data/knowledge-sample/02-search-feedback.md`
- `demo-data/knowledge-sample/03-operations-metrics.md`
- `demo-data/knowledge-sample/99-broken-scan.txt`
- `demo-data/knowledge-sample/manifest.json`

## 已知限制

- 当前基线使用内存版 demo 引擎，目的是用低成本方式验证业务链路和文档表达。
- 真实后端、对象存储、向量数据库和用户系统已有工程基础；后续需要把该 demo 链路升级为 API 级集成测试。
- 截图为产品基线示意图，后续应由真实后台页面替换。

## 后续建议

1. 将 demo 引擎替换为真实上传、解析和检索 API 的集成测试。
2. 将运营指标接入真实事件和监控系统。
3. 建立真实运营后台页面并生成自动化截图。
4. 发布 Git tag 和 GitHub Release，并附上测试输出与截图。
