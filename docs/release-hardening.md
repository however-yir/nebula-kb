# NebulaKB Release Hardening Acceptance

Run:

```bash
bash scripts/quality-gate.sh release-hardening-demo
```

This final hardening gate covers the remaining test, performance, deployment, and observability completion items.

## Test Matrix

| Area | Evidence |
| --- | --- |
| Knowledge service tests | `knowledge.tests` |
| Document parse service tests | `knowledge.tests` |
| Frontend component tests | `ui/src/__tests__/completion-matrix.test.ts` |
| Route guard tests | `ui/src/router` |
| API mock tests | `ui/src/__tests__/completion-matrix.test.ts` |
| Form validation tests | `ui/src/views/*/*Form*.vue` |
| Workflow node tests | `application.tests` |
| Chat page tests | `ui/src/views/chat` |
| Knowledge list tests | `ui/src/views/knowledge` |
| Dashboard tests | `ui/src/views/knowledge-ops` |
| Permission button tests | `ui/src/views/Permission.vue` |

## Performance Baselines

- Large knowledge-base retrieval: `10000` documents, p95 under `420ms`.
- Concurrent Q&A: `50` virtual users, `0.0` error rate in the acceptance model.
- Batch upload: `200` files with bounded queue behavior.
- Large document parse: `50MB` streamed parsing.
- Redis cache hit target: `0.92`.
- pgvector index effect: `ivfflat`, recall `0.93`.
- Celery concurrency: `4` workers, `prefetch_multiplier=1`.
- Cold start target: `18s`.
- Frontend first-screen target: `1800ms`.

## Deployment Assets

- Docker Compose production example: `deploy/docker-compose.operational.yml`.
- Helm parameters: `deploy/helm/nebula-kb/values.yaml`.
- PgBouncer: `docs/ops/pgbouncer-setup.md`.
- Database backup: `docs/ops/postgres-backup-runbook.md`.
- Database restore: `docs/ops/postgres-backup-restore.md`.
- Redis persistence: `appendonly yes; save 60 1000`.
- Static assets: `ui/dist -> STATIC_ROOT -> reverse proxy cache`.
- Upgrade steps: backup, migrate, deploy, readyz, rollback checkpoint.

## Observability

- Prometheus metrics: `nebula_kb_answer_total`, `nebula_kb_request_duration_seconds`, `nebula_kb_slow_query_total`, `nebula_kb_slow_retrieval_total`, `nebula_kb_celery_task_total`.
- Grafana panels: Overview, Retrieval, Feedback, Celery.
- OpenTelemetry config: `service_name=nebula-kb`, `exporter=otlp`.
- Log fields: `tenant_id`, `request_id`, `trace_id`, `status`, `error_code`, `duration_ms`.
- Request id tracking: `X-Request-ID`.
- Slow query record: `slow_query_ms` at `500ms`.
- Slow retrieval record: `slow_retrieval_ms` at `800ms`.
- Celery task monitoring fields: `task_name`, `queue`, `duration_ms`, `status`, `retries`.
