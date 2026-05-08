#!/usr/bin/env bash
# yourrag automated backup script
# Usage: ./backup.sh [--full] [--s3-bucket BUCKET] [--retain-days DAYS]
set -euo pipefail

BACKUP_DIR="${YOURRAG_BACKUP_DIR:-/data/backups/yourrag}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS="${RETAIN_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
FULL_BACKUP="${FULL_BACKUP:-false}"

MYSQL_HOST="${MYSQL_HOST:-mysql}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DB="${MYSQL_DBNAME:-yourrag}"

MINIO_HOST="${MINIO_HOST:-minio}"
MINIO_USER="${MINIO_USER:-yourrag}"
MINIO_PASSWORD="${MINIO_PASSWORD:-}"

mkdir -p "${BACKUP_DIR}/${TIMESTAMP}"

echo "[$(date)] Starting yourrag backup: ${TIMESTAMP}"

# --- MySQL backup ---
echo "[$(date)] Backing up MySQL database '${MYSQL_DB}'..."
mysqldump -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" \
  --single-transaction --routines --triggers --events \
  "${MYSQL_DB}" > "${BACKUP_DIR}/${TIMESTAMP}/mysql_${MYSQL_DB}.sql"
gzip "${BACKUP_DIR}/${TIMESTAMP}/mysql_${MYSQL_DB}.sql"
echo "[$(date)] MySQL backup complete: $(du -sh ${BACKUP_DIR}/${TIMESTAMP}/mysql_${MYSQL_DB}.sql.gz | cut -f1)"

# --- MinIO backup (knowledge base files) ---
if command -v mc &>/dev/null; then
  echo "[$(date)] Backing up MinIO buckets..."
  mc alias set myminio "http://${MINIO_HOST}:9000" "${MINIO_USER}" "${MINIO_PASSWORD}"
  mc ls myminio/ 2>/dev/null | awk '{print $NF}' | while read -r bucket; do
    mc cp --recursive "myminio/${bucket}/" "${BACKUP_DIR}/${TIMESTAMP}/minio_${bucket}/" 2>/dev/null || true
  done
  echo "[$(date)] MinIO backup complete."
else
  echo "[$(date)] WARNING: mc (MinIO client) not found, skipping MinIO backup"
fi

# --- Config backup ---
echo "[$(date)] Backing up configuration..."
cp -r /ragflow/conf "${BACKUP_DIR}/${TIMESTAMP}/conf" 2>/dev/null || true

# --- S3 upload ---
if [[ -n "${S3_BUCKET}" ]] && command -v aws &>/dev/null; then
  echo "[$(date)] Uploading to S3: ${S3_BUCKET}/yourrag-backup/${TIMESTAMP}/"
  aws s3 sync "${BACKUP_DIR}/${TIMESTAMP}/" "s3://${S3_BUCKET}/yourrag-backup/${TIMESTAMP}/"
  echo "[$(date)] S3 upload complete."
fi

# --- Cleanup old backups ---
if [[ "${RETAIN_DAYS}" -gt 0 ]]; then
  echo "[$(date)] Cleaning up backups older than ${RETAIN_DAYS} days..."
  find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime +${RETAIN_DAYS} -exec rm -rf {} + 2>/dev/null || true
  echo "[$(date)] Cleanup complete."
fi

TOTAL_SIZE=$(du -sh "${BACKUP_DIR}/${TIMESTAMP}" | cut -f1)
echo "[$(date)] Backup complete: ${BACKUP_DIR}/${TIMESTAMP} (${TOTAL_SIZE})"
