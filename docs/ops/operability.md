# NebulaKB 可运维部署说明

本文定义 NebulaKB 从一体化运行迁移到分离部署后的运行契约。目标是：服务可独立部署、配置可切换、故障可恢复、发布可回退。

## 部署形态

| 服务 | 职责 | 启动命令 | 健康检查 |
| --- | --- | --- | --- |
| web | 管理端、聊天端、API | `./scripts/run-service.sh web` | `GET /healthz`、`GET /readyz` on `:8080` |
| worker | Celery 默认队列和模型队列 | `./scripts/run-service.sh worker` | `GET /healthz`、`GET /readyz` on `:8081` |
| scheduler | APScheduler 定时任务调度 | `./scripts/run-service.sh scheduler` | `GET /healthz`、`GET /readyz` on `:6060` |
| local-model | 本地模型推理服务 | `./scripts/run-service.sh local_model` | `GET /healthz`、`GET /readyz` on `:11636` |
| PostgreSQL | 主业务库，要求 pgvector | `postgres` container | `pg_isready` |
| Redis | 缓存、Celery broker、任务锁 | `redis` container | `redis-cli ping` |
| object-storage | 文件与对象存储，MinIO/S3 兼容 | `minio` container | `/minio/health/ready` |

推荐使用 `deploy/docker-compose.operational.yml` 作为分离部署基线：

```bash
docker compose --env-file deploy/env/dev.env -f deploy/docker-compose.operational.yml up -d
```

切换环境文件时设置 `NEBULA_ENV_FILE`，例如：

```bash
NEBULA_ENV_FILE=./env/prod.env docker compose --env-file deploy/env/prod.env -f deploy/docker-compose.operational.yml up -d
```

## 环境变量契约

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `APP_ENV` / `NEBULA_ENVIRONMENT` | 是 | `dev`、`test`、`prod` |
| `SECRET_KEY` / `SECRET_KEY_FILE` | prod 必填 | Django 签名密钥，生产必须通过密钥系统注入 |
| `DATABASE_URL` / `DATABASE_URL_FILE` | 是 | PostgreSQL 连接串，如 `postgresql://user:pass@postgres:5432/nebula` |
| `REDIS_URL` / `REDIS_URL_FILE` | 是 | Redis 连接串，如 `redis://:pass@redis:6379/0` |
| `STORAGE_BACKEND` | 是 | `local` 或 `s3` |
| `STORAGE_ENDPOINT` | s3 必填 | S3/MinIO endpoint |
| `STORAGE_BUCKET` | s3 必填 | 存储桶 |
| `STORAGE_ACCESS_KEY` / `STORAGE_ACCESS_KEY_FILE` | s3 必填 | 对象存储访问密钥 |
| `STORAGE_SECRET_KEY` / `STORAGE_SECRET_KEY_FILE` | s3 必填 | 对象存储密钥 |
| `STORAGE_HEALTHCHECK_URL` | 建议 | 对象存储健康检查 URL |
| `NEBULA_LOCAL_MODEL_HOST` | 是 | web/worker/scheduler 访问模型服务的主机名 |
| `NEBULA_MODEL_SERVICE_HEALTHCHECK_ENABLED` | 否 | 是否把模型服务纳入 `/readyz` |

旧的 `LZKB_DB_*`、`LZKB_REDIS_*` 和 `MAXKB_*` 变量仍然兼容。若同时配置 `DATABASE_URL` 和拆分字段，以 `DATABASE_URL` 解析结果为准。

## 配置切换

环境变量模式：

```bash
export NEBULA_CONFIG_TYPE=ENV
set -a
. deploy/env/dev.env
set +a
python apps/manage.py check
```

文件模式：

```bash
export NEBULA_CONFIG_TYPE=FILE
export NEBULA_ENVIRONMENT=prod
export NEBULA_CONF_DIR=/opt/nebulakb/conf
# /opt/nebulakb/conf/config.prod.yml 或 /opt/nebulakb/conf/config/prod.yml 会优先加载
python apps/manage.py check
```

生产环境应使用 `*_FILE` 从 Docker/Kubernetes secret 注入敏感值，避免把密钥写进镜像、仓库或普通环境模板。

## 健康检查语义

`/healthz` 只证明进程存活，不访问外部依赖。

`/readyz` 会检查：

- PostgreSQL：执行 `SELECT 1`
- Redis/cache：写入并读取短 TTL key
- local-model：web、worker、scheduler 会请求模型服务 `/healthz`
- object-storage：当 `STORAGE_BACKEND=s3` 时，优先请求 `STORAGE_HEALTHCHECK_URL`；未配置该 URL 时，使用 S3 `head_bucket`

发布系统只应在 `/readyz` 返回 200 后切流量。

本地验证命令：

```bash
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8080/readyz
```

若 `/healthz` 成功但 `/readyz` 失败，应优先检查 PostgreSQL、Redis、local-model 和 object storage 的连接配置。开发模式下，后端默认监听 `:8080`，管理前端默认监听 `:5173`，聊天前端默认监听 `:5174`。

## 本地启动排查矩阵

首次启动失败时，按依赖顺序排查，不要先改业务代码：

| 症状 | 检查命令 | 处理方式 |
| --- | --- | --- |
| `.env` 无法启动或脚本拒绝继续 | `grep -n 'CHANGE_ME_' .env` | 复制 `.env.example` 后替换所有占位密钥；`SECRET_KEY`、数据库密码、Redis 密码每个环境都应唯一 |
| Docker 依赖未启动 | `docker compose --env-file .env -f docker-compose.dev.yml ps` | 启动 Docker Desktop 后执行 `./scripts/bootstrap-local.sh --start` |
| PostgreSQL 连接失败 | `docker compose --env-file .env -f docker-compose.dev.yml logs postgres` 和 `pg_isready -h 127.0.0.1 -p "${NEBULA_DB_PORT:-5432}"` | 确认 `NEBULA_DB_HOST`、`NEBULA_DB_PORT`、`NEBULA_DB_USER`、`NEBULA_DB_PASSWORD` 与 `.env` 一致 |
| Redis 连接失败或 `NOAUTH` | `docker compose --env-file .env -f docker-compose.dev.yml logs redis` 和 `redis-cli -h 127.0.0.1 -p "${NEBULA_REDIS_PORT:-6379}" ping` | 确认 `REDIS_URL` 与 `NEBULA_REDIS_PASSWORD` 同步；带密码时使用 `redis-cli -a "$NEBULA_REDIS_PASSWORD" ping` |
| pgvector 扩展缺失 | `docker compose --env-file .env -f docker-compose.dev.yml exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dx vector"'` | 执行 `./scripts/bootstrap-local.sh --start`，或手动运行 `CREATE EXTENSION IF NOT EXISTS vector;` |
| 端口冲突 | `lsof -nP -iTCP:5432 -iTCP:6379 -iTCP:8080 -iTCP:5173 -iTCP:5174 -sTCP:LISTEN` | 停止占用进程，或在 `.env` 中调整 `NEBULA_DB_PORT`、`NEBULA_REDIS_PORT`，前端端口在 Vite 配置或启动参数中调整 |
| Python 依赖缺失 | `python -V && python -m pip check` | 使用 Python 3.11，重新执行 `python -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -e .` |
| 前端依赖缺失 | `node -v && npm -v && npm ls --depth=0` | 使用 Node 20，在 `ui/` 下执行 `npm ci`，再运行 `npm run dev` 或 `npm run chat` |
| 迁移后仍无法访问 | `python apps/manage.py check && python apps/manage.py migrate --plan` | 先修复 Django check；确认数据库指向本地开发库后再执行迁移 |

## 本地数据目录与持久化

`NEBULA_DATA_DIR` 是新的运行时数据目录入口，`LZKB_DATA_DIR` 和 `MAXKB_DATA_DIR` 仅作为兼容变量保留。开发模板默认使用 `/tmp/nebula`，用于模型缓存、临时文件和日志；长期演示或共享环境应把目录换成可持久化路径。

| 数据 | 默认/入口 | 说明 |
| --- | --- | --- |
| 应用运行数据 | `NEBULA_DATA_DIR=/tmp/nebula` | 本地开发可清理；演示环境建议改为 `~/.nebula-kb` 或宿主持久目录 |
| 日志 | `${NEBULA_DATA_DIR}/logs` | 由运行时创建，排查启动和任务失败时优先查看 |
| 模型和 tokenizer 缓存 | `HF_HOME`、`TIKTOKEN_CACHE_DIR`、`NEBULA_EMBEDDING_MODEL_PATH` | `.env.example` 默认放在 `/tmp/nebula/model/**` |
| PostgreSQL 数据 | Docker volume `nebula_postgres_data` | 删除 volume 会丢失本地库；删除前先按备份 runbook 导出 |
| Redis 数据 | Docker volume `nebula_redis_data` | 本地缓存和任务状态；重建前确认没有未完成任务 |
| Ollama 模型 | Docker volume `nebula_ollama_data` | 仅在 `--with-ollama` 或 compose profile 启用时使用 |

清理本地数据前，先停止服务并确认备份：

```bash
docker compose --env-file .env -f docker-compose.dev.yml down
docker volume ls | grep nebula_
```

## 发布和回滚

构建发布镜像前必须先通过 `.github/workflows/nebulakb-tests.yml`。`build-and-push.yml` 已把测试工作流作为前置依赖。

生产切流前先运行安全基线：

```bash
NEBULA_ENVIRONMENT=prod scripts/production-security-check.sh
```

该命令会检查 `SECRET_KEY`、`ALLOWED_HOSTS`、数据库、Redis 和 `DEBUG`，禁止占位密钥进入生产。

发布后健康检查：

```bash
./scripts/post-release-healthcheck.sh https://nebulakb.example.com
```

一键回滚到上一镜像：

```bash
NEBULA_RELEASE_URL=https://nebulakb.example.com ./scripts/rollback.sh ghcr.io/however-yir/nebulakb/nebula-kb:v2.0.0
```

回滚流程会拉取指定镜像、重启 `web`/`worker`/`scheduler`/`local-model`，并在配置了 `NEBULA_RELEASE_URL` 时执行发布后健康检查。`LZKB_RELEASE_URL` 仍作为兼容变量可用。
