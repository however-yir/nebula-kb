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

## 发布和回滚

构建发布镜像前必须先通过 `.github/workflows/nebulakb-tests.yml`。`build-and-push.yml` 已把测试工作流作为前置依赖。

发布后健康检查：

```bash
./scripts/post-release-healthcheck.sh https://nebulakb.example.com
```

一键回滚到上一镜像：

```bash
NEBULA_RELEASE_URL=https://nebulakb.example.com ./scripts/rollback.sh ghcr.io/however-yir/nebulakb/nebula-kb:v2.0.0
```

回滚流程会拉取指定镜像、重启 `web`/`worker`/`scheduler`/`local-model`，并在配置了 `NEBULA_RELEASE_URL` 时执行发布后健康检查。`LZKB_RELEASE_URL` 仍作为兼容变量可用。
