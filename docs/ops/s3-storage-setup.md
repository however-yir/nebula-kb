# S3 / MinIO Storage Setup

## Configuration
Set these environment variables for S3-compatible storage:

```env
STORAGE_BACKEND=s3
STORAGE_ENDPOINT=http://minio:9000
STORAGE_BUCKET=nebula
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_REGION=us-east-1
STORAGE_FORCE_PATH_STYLE=true
```

## MinIO (Recommended for Self-Hosted)
MinIO is included in `deploy/docker-compose.operational.yml`. The init container creates the default bucket.

## AWS S3
```env
STORAGE_BACKEND=s3
STORAGE_ENDPOINT=
STORAGE_BUCKET=your-nebula-bucket
STORAGE_ACCESS_KEY=AKIA...
STORAGE_SECRET_KEY=...
STORAGE_REGION=us-east-1
STORAGE_FORCE_PATH_STYLE=false
```

## Migration from Local Storage
Files stored locally are in the `oss_file` table (PostgreSQL large objects). To migrate:

1. Export files: `python manage.py dumpdata oss.File`
2. Switch `STORAGE_BACKEND=s3`
3. Re-import files (they'll be stored in S3 on next access)
