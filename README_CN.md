# NebulaKB

NebulaKB 是一个面向私有化部署和二次开发的知识运营中枢。

## 项目定位

本仓库用于：
- 构建企业内部知识问答与智能助手；
- 基于业务场景定制模型路由与工具工作流；
- 去除上游品牌与默认配置耦合；
- 建立可长期独立演进的技术底座。

## 已完成的改造

### 1) 命名与命名空间
- 后端 Django 命名空间从 `lzkb` 分阶段迁移为 `nebula`；
- 运行时 settings 模块改为 `nebula.settings`；
- 前端全局对象新增 `window.NEBULA`，`window.LZKB` 仅作为兼容桥；
- 本地语言缓存键从 `LZKB-locale` 迁移为 `NEBULA-locale`；
- 前端默认标题改为 `NebulaKB`。

### 2) 配置去敏与安全加固
- 将敏感默认值改为占位符：
  - `CHANGE_ME_DB_PASSWORD`
  - `CHANGE_ME_REDIS_PASSWORD`
- 内置默认用户密码改为 `ChangeMe@1234!`（生产必须覆盖）；
- 在 `installer/start-all.sh` 增加占位密码启动拦截，防止误上线。

### 3) 配置模板补齐
- 新增根目录 [`config_example.yml`](./config_example.yml)（文件方式配置）；
- 新增根目录 [`.env.example`](./.env.example)（环境变量方式配置）；
- 推荐使用 `NEBULA_` 前缀，同时兼容旧 `LZKB_` 与 `MAXKB_` 前缀，降低迁移成本。

### 4) 品牌与链接替换
- 已替换前端默认品牌字段和主要外链；
- 文档改写为 fork 项目视角，便于后续独立维护。

## 快速部署（Docker）

```bash
docker run -d \
  --name=nebula-kb \
  --restart=always \
  -p 8080:8080 \
  -e POSTGRES_PASSWORD='你的强密码' \
  -e REDIS_PASSWORD='你的强密码' \
  -e NEBULA_CONFIG_TYPE=ENV \
  -e NEBULA_DB_NAME=nebula \
  -e NEBULA_DB_HOST=127.0.0.1 \
  -e NEBULA_DB_PORT=5432 \
  -e NEBULA_DB_USER=root \
  -e NEBULA_DB_PASSWORD='你的强密码' \
  -e NEBULA_REDIS_HOST=127.0.0.1 \
  -e NEBULA_REDIS_PORT=6379 \
  -e NEBULA_REDIS_PASSWORD='你的强密码' \
  -v ~/.nebula-kb:/opt/maxkb \
  nebulakb/nebula-kb:latest
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

### 首次启动检查清单

首次运行或换机器演示前，按顺序确认：

1. `.env` 已由 `.env.example` 复制，且所有 `CHANGE_ME_*` 值已经替换；`scripts/bootstrap-local.sh` 会阻止占位密码启动。
2. Python 使用 3.11，虚拟环境已激活，`pip install -e .` 已完成；前端使用 Node 20 并执行过 `npm ci`。
3. Docker Desktop 正在运行；如使用本地依赖栈，执行 `docker compose --env-file .env -f docker-compose.dev.yml ps` 能看到 `postgres` 和 `redis`。
4. `5432`、`6379`、`8080`、`5173`、`5174` 未被占用；如被占用，先在 `.env` 调整 `NEBULA_DB_PORT`、`NEBULA_REDIS_PORT` 或前端 dev server 端口。
5. PostgreSQL 使用 `pgvector/pgvector:pg16`，并能执行 `CREATE EXTENSION IF NOT EXISTS vector;`。
6. 本地数据目录已明确：开发默认使用 `NEBULA_DATA_DIR=/tmp/nebula`；Docker 演示或长期数据请挂载到持久目录，例如 `~/.nebula-kb`。
7. 运行 `python apps/manage.py check` 和 `python apps/manage.py migrate` 后再启动 `python main.py dev web`。

常见启动失败排查见 [docs/ops/operability.md#本地启动排查矩阵](docs/ops/operability.md#本地启动排查矩阵)。

### 前端

```bash
cd ui
npm install
npm run dev
```

### 启动成功检查

本地开发默认端口：

| 服务 | 地址 | 成功标准 |
| --- | --- | --- |
| 后端 API / 管理端静态入口 | `http://localhost:8080/admin` | 页面可访问，API 请求不返回启动错误 |
| 聊天端静态入口 | `http://localhost:8080/chat` | 页面可访问，聊天端资源可加载 |
| 管理前端 Vite | `http://localhost:5173` | Vite dev server 启动成功 |
| 聊天前端 Vite | `http://localhost:5174` | chat mode dev server 启动成功 |

健康检查：

```bash
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8080/readyz
```

`/healthz` 只验证进程存活；`/readyz` 会验证 PostgreSQL、Redis、模型服务和对象存储等依赖是否可用。发布或演示前应以 `/readyz` 返回成功作为继续操作的条件。

最小演示闭环：

1. 登录管理端并创建知识库。
2. 上传 `demo-data/knowledge-sample/` 中的示例资料。
3. 等待解析、切片、向量化完成。
4. 在检索或问答页面提出一个命中示例资料的问题。
5. 提交一次点赞或点踩反馈。
6. 打开知识运营大盘，确认命中、低质答案或待更新知识指标可见。

## 与上游版本的主要差异

当前 fork 重点差异：
- 核心运行包命名去耦（`lzkb` -> `nebula`，分阶段兼容）；
- 默认凭据与启动安全策略强化；
- 前端运行时品牌键值与文档替换；
- 面向独立仓库运营的部署与维护说明。

后续计划：
- 按业务域拆分与重构核心模块；
- 完善模型提供商抽象与插件治理；
- 补齐测试、质量门禁、依赖锁定和 CI 稳定性。

## 质量与发布验收

NebulaKB 的可靠性目标是先覆盖最小验收闭环，再逐步提高 CI 拦截能力：

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

> NebulaKB - 面向私有化部署的知识运营中枢。

当前 Topics：

`nebulakb`, `knowledge-ops`, `rag`, `knowledge-base`, `llm`, `django`, `vue3`, `ollama`, `redis`, `postgresql`

## 许可证

本项目基于 GPLv3 上游项目 fork，继续遵循 GPLv3 义务。

请参考：
- [LICENSE](./LICENSE)
- [NOTICE-NebulaKB.md](./NOTICE-NebulaKB.md)
