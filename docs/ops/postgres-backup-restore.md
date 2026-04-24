# PostgreSQL 备份与恢复 SOP

适用范围：NebulaKB PostgreSQL 主库。目标是在误操作、升级失败或数据损坏时，可以用经过校验的备份恢复服务。

## 备份策略

- 频率：生产环境至少每日一次全量逻辑备份；高频写入场景应补充 WAL/PITR。
- 保留：默认保留 7 天日备份、4 周周备份、3 个月月备份。
- 存储：备份文件必须离开数据库主机，上传到对象存储或备份系统。
- 校验：每个 `.dump` 旁边必须保留 `.sha256`，并定期做演练恢复。

## 手动备份

使用 `DATABASE_URL`：

```bash
export DATABASE_URL='postgresql://nebula:password@postgres:5432/nebula'
./scripts/backup-postgres.sh
```

使用拆分变量：

```bash
export NEBULA_DB_HOST=postgres
export NEBULA_DB_PORT=5432
export NEBULA_DB_NAME=nebula
export NEBULA_DB_USER=nebula
export NEBULA_DB_PASSWORD='password'
./scripts/backup-postgres.sh /secure-backups/nebula-$(date +%F).dump
```

备份脚本会生成 `pg_dump --format=custom` 文件和 SHA256 校验文件。

## 恢复前检查

1. 确认目标环境和备份时间点。
2. 暂停写流量：停止 web、worker、scheduler，或在网关层摘流量。
3. 记录当前镜像 tag、数据库连接串、备份文件路径。
4. 如果当前库仍可访问，先做一次事故现场备份。
5. 校验备份：

```bash
sha256sum -c /secure-backups/nebula-2026-04-21.dump.sha256
```

## 执行恢复

```bash
export DATABASE_URL='postgresql://nebula:password@postgres:5432/nebula'
export NEBULA_RESTORE_CONFIRM=yes
./scripts/restore-postgres.sh /secure-backups/nebula-2026-04-21.dump
```

恢复脚本使用 `pg_restore --clean --if-exists --no-owner`。恢复目标必须是确认过的目标库，避免误覆盖生产。

## 恢复后验证

1. 执行数据库连通性检查：

```bash
python apps/manage.py healthcheck --ready --json
```

2. 重启服务：

```bash
docker compose -f deploy/docker-compose.operational.yml up -d web worker scheduler local-model
```

3. 检查探针：

```bash
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8080/readyz
```

4. 抽查核心业务：登录、知识库检索、聊天、文件访问。

## 失败处理

- 恢复失败且原库未删除：停止恢复，保留日志和事故现场备份。
- 恢复成功但应用不健康：先查看 `/readyz` 中失败的依赖，再决定回滚镜像或修复配置。
- 发布失败需要回退：执行 `./scripts/rollback.sh <previous-image>`，回滚后再运行发布后健康检查。
