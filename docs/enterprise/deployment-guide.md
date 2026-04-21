# LZKB 部署手册

本文面向交付、运维和二开团队，说明企业交付版部署步骤和上线检查。

## 基础依赖

推荐环境：

- Python 3.11
- PostgreSQL 16
- Redis 7
- Linux x86_64 或容器环境
- 反向代理：Nginx、Ingress 或云负载均衡

关键环境变量：

| 变量 | 说明 |
| --- | --- |
| `LZKB_CONFIG_TYPE` | 配置来源，推荐生产使用 `ENV` |
| `LZKB_DB_NAME` | PostgreSQL 数据库名 |
| `LZKB_DB_HOST` | PostgreSQL 地址 |
| `LZKB_DB_PORT` | PostgreSQL 端口 |
| `LZKB_DB_USER` | PostgreSQL 用户 |
| `LZKB_DB_PASSWORD` | PostgreSQL 密码 |
| `LZKB_REDIS_HOST` | Redis 地址 |
| `LZKB_REDIS_PORT` | Redis 端口 |
| `LZKB_REDIS_PASSWORD` | Redis 密码 |
| `LZKB_CORE_WORKER` | Web worker 数量 |

生产环境禁止保留 `CHANGE_ME_DB_PASSWORD` 或 `CHANGE_ME_REDIS_PASSWORD`。

## 本地验证部署

```bash
python -m uv pip install -r pyproject.toml
python main.py upgrade_db
python main.py dev web
```

默认访问：

- 管理端：`http://127.0.0.1:8080/admin`
- API 前缀：`/admin/api/`

## Docker Compose 依赖

仓库提供 `docker-compose.dev.yml` 启动 PostgreSQL、Redis 和可选 Ollama：

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d postgres redis
python main.py upgrade_db
python main.py start web
```

如启用 Ollama：

```bash
docker compose -f docker-compose.dev.yml --profile ollama up -d ollama
```

## 数据库迁移

上线或升级必须执行：

```bash
python main.py upgrade_db
```

本次企业能力基线新增审计契约字段：

- `log.event_name`
- `log.actor`
- `log.resource`
- `log.timestamp`
- `log.result`

迁移后检查：

```sql
select event_name, actor, resource, timestamp, result
from log
order by timestamp desc
limit 5;
```

## 反向代理

建议：

- 强制 HTTPS。
- 将真实客户端 IP 写入 `X-Forwarded-For`。
- 限制 `/admin` 入口来源网段。
- 对公开聊天 API 单独配置请求体大小和超时。

Nginx 示例片段：

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
client_max_body_size 100m;
proxy_read_timeout 300s;
```

## SSO 交付

一期 SSO 按以下边界交付：

1. 客户已有 IdP 时，优先通过外部 OIDC/SAML 网关完成认证，再将可信身份传递给 LZKB 的登录扩展。
2. 原生 OIDC/SAML 对接属于客户化扩展，必须复用 LZKB Token、RBAC 和审计日志契约。
3. SSO 用户的 `source` 字段不得为 `LOCAL`，登录事件必须写入 `event_name=login` 或等价事件名。

## 上线检查

上线前必须完成：

- 使用非默认数据库和 Redis 密码。
- 执行数据库迁移并确认成功。
- 创建平台管理员并修改默认密码。
- 创建至少一个工作空间和工作空间管理员。
- 验证 API Key 启停、过期和跨域设置。
- 验证审计查询接口可返回登录、管理、数据访问和配置变更事件。
- 验证运营指标接口返回调用量、成本、活跃度和失败率。

## 备份与恢复

每日备份：

- PostgreSQL 全量备份。
- Redis 持久化文件或缓存重建策略。
- `/opt/maxkb` 或 `LZKB_DATA_DIR` 数据目录。
- 模型文件与上传文件目录。

恢复后必须验证：

1. 用户可登录。
2. 工作空间资源列表可打开。
3. 审计日志可查询。
4. 应用 API Key 可调用。
5. 运营指标可计算。
