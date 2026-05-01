# PostgreSQL Backup Runbook

## Automated Backups
Use `scripts/cron-backup.sh` for automated daily backups with retention.

```bash
# Manual backup
bash scripts/backup-postgres.sh

# Cron backup (with 7-day retention)
BACKUP_RETENTION_DAYS=7 bash scripts/cron-backup.sh
```

## Celery Scheduled Backup
The task `ops.postgres_backup` can be scheduled via django-celery-beat:
```python
from django_celery_beat.models import PeriodicTask, CrontabSchedule
```

## Restore
```bash
pg_restore --clean --if-exists --no-owner \
  -h 127.0.0.1 -p 5432 -U root -d nebula \
  backups/postgres/nebula-YYYYMMDD-HHMMSS.dump
```

## Point-in-Time Recovery
Enable WAL archiving in PostgreSQL and use `pg_basebackup` + WAL replay.

## S3 Archival
Set `NEBULA_BACKUP_DIR=s3://bucket/nebula-backups/` with AWS CLI configured.
