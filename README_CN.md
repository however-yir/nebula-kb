# LZKB

LZKB 是一个面向私有化部署和二次开发的企业级智能体与知识库平台（基于上游项目定制化 fork）。

## 这个 Fork 的定位

本仓库用于：
- 构建企业内部知识问答与智能助手；
- 基于业务场景定制模型路由与工具工作流；
- 去除上游品牌与默认配置耦合；
- 建立可长期独立演进的技术底座。

## 已完成的改造

### 1) 命名与命名空间
- 后端 Django 命名空间从 `maxkb` 迁移为 `lzkb`；
- 运行时 settings 模块改为 `lzkb.settings`；
- 前端全局对象从 `window.MaxKB` 改为 `window.LZKB`；
- 本地语言缓存键从 `MaxKB-locale` 改为 `LZKB-locale`；
- 前端默认标题改为 `LZKB`。

### 2) 配置去敏与安全加固
- 将敏感默认值改为占位符：
  - `CHANGE_ME_DB_PASSWORD`
  - `CHANGE_ME_REDIS_PASSWORD`
- 内置默认用户密码改为 `ChangeMe@1234!`（生产必须覆盖）；
- 在 `installer/start-all.sh` 增加占位密码启动拦截，防止误上线。

### 3) 配置模板补齐
- 新增根目录 [`config_example.yml`](./config_example.yml)（文件方式配置）；
- 新增根目录 [`.env.example`](./.env.example)（环境变量方式配置）；
- 推荐使用 `LZKB_` 前缀，同时兼容旧 `MAXKB_` 前缀，降低迁移成本。

### 4) 品牌与链接替换
- 已替换前端默认品牌字段和主要外链；
- 文档改写为 fork 项目视角，便于后续独立维护。

## 快速部署（Docker）

```bash
docker run -d \
  --name=lzkb \
  --restart=always \
  -p 8080:8080 \
  -e POSTGRES_PASSWORD='你的强密码' \
  -e REDIS_PASSWORD='你的强密码' \
  -e LZKB_CONFIG_TYPE=ENV \
  -e LZKB_DB_NAME=lzkb \
  -e LZKB_DB_HOST=127.0.0.1 \
  -e LZKB_DB_PORT=5432 \
  -e LZKB_DB_USER=root \
  -e LZKB_DB_PASSWORD='你的强密码' \
  -e LZKB_REDIS_HOST=127.0.0.1 \
  -e LZKB_REDIS_PORT=6379 \
  -e LZKB_REDIS_PASSWORD='你的强密码' \
  -v ~/.lzkb:/opt/maxkb \
  your-dockerhub-or-registry/lzkb:latest
```

访问地址：
- 管理端：`http://<你的地址>:8080/admin`
- 对话端：`http://<你的地址>:8080/chat`

生产化部署建议使用分离形态：`web` / `worker` / `scheduler` / PostgreSQL / Redis / object storage。环境变量契约、`/healthz` / `/readyz`、备份恢复和回滚流程见 [docs/ops/operability.md](docs/ops/operability.md) 与 [docs/ops/postgres-backup-restore.md](docs/ops/postgres-backup-restore.md)。

## 本地开发

### 后端

```bash
python -m uv pip install -r pyproject.toml
python apps/manage.py migrate
python main.py dev web
```

### 一键快速安装（推荐）

macOS:

```bash
./scripts/quick-install-mac.sh
# 如需一起拉起 Ollama:
# ./scripts/quick-install-mac.sh --with-ollama
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-install-win.ps1
# 如需一起拉起 Ollama:
# powershell -ExecutionPolicy Bypass -File .\scripts\quick-install-win.ps1 -WithOllama
```

脚本会自动：

1. 初始化 `.env` 并替换 `CHANGE_ME_*` 占位密钥；
2. 创建 `.venv` 并安装依赖；
3. 拉起 PostgreSQL / Redis（可选 Ollama）并自动确保 `pgvector` 扩展；
4. 执行数据库迁移。

### 前端

```bash
cd ui
npm install
npm run dev
```

## 与上游版本的主要差异

当前 fork 重点差异：
- 核心运行包命名去耦（`maxkb` -> `lzkb`）；
- 默认凭据与启动安全策略强化；
- 前端运行时品牌键值与文档替换；
- 面向独立仓库运营的部署与维护说明。

后续计划：
- 按业务域拆分与重构核心模块；
- 完善模型提供商抽象与插件治理；
- 补齐测试、质量门禁、依赖锁定和 CI 稳定性。

## 质量与发布验收

LZKB 的可靠性目标是先覆盖最小验收闭环，再逐步提高 CI 拦截能力：

`登录 -> 知识库 -> 上传 -> 检索 -> 应用 -> 权限 -> API Key`

质量体系采用四层测试：单元、集成、API 回归、E2E。高风险模块优先覆盖认证、权限、token、文件上传、公开接口、工作流执行，并按 50% -> 60% -> 核心模块 70%+ 推进覆盖率。

发布前请执行固定检查：

```bash
bash scripts/quality-gate.sh release
```

详细方案见：

- [可靠性验收方案](./docs/quality/reliability-acceptance.md)
- [发布检查清单](./docs/quality/release-checklist.md)

## 企业交付基线

一期企业能力边界聚焦“权限可控、行为可追溯、数据可隔离、客户可交付”，覆盖工作空间、RBAC、审计日志、SSO 交付边界、API Key、配额限流和基础可观测性。

交付文档见：

- [企业交付文档索引](./docs/enterprise/README.md)
- [一期企业能力边界](./docs/enterprise/enterprise-capability-boundary.md)
- [管理员手册](./docs/enterprise/administrator-guide.md)
- [部署手册](./docs/enterprise/deployment-guide.md)
- [安全说明](./docs/enterprise/security-notes.md)
- [故障处理文档](./docs/enterprise/troubleshooting-guide.md)

## 仓库描述与 Topics（已应用）

当前仓库描述：

> LZKB - 面向私有化部署的企业级智能体与知识库平台。

当前 Topics：

`lzkb`, `ai`, `rag`, `knowledge-base`, `llm`, `django`, `vue3`, `ollama`, `redis`, `postgresql`

## 许可证

本项目基于 GPLv3 上游项目 fork，继续遵循 GPLv3 义务。

请参考：
- [LICENSE](./LICENSE)
- [NOTICE-LZKB.md](./NOTICE-LZKB.md)
