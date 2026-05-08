#!/usr/bin/env bash
# yourrag cold data archival script
# Archives old documents/conversations to cheaper storage
set -euo pipefail

MYSQL_HOST="${MYSQL_HOST:-mysql}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DB="${MYSQL_DBNAME:-yourrag}"
ARCHIVE_DAYS="${ARCHIVE_DAYS:-180}"

S3_BUCKET="${S3_BUCKET:-}"
ARCHIVE_DIR="${YOURRAG_ARCHIVE_DIR:-/data/archive/yourrag}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "${ARCHIVE_DIR}/${TIMESTAMP}"

echo "[$(date)] Starting cold archive for data older than ${ARCHIVE_DAYS} days..."

# Export old documents
echo "[$(date)] Exporting old documents..."
mysqldump -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" \
  --single-transaction --where="create_date < DATE_SUB(NOW(), INTERVAL ${ARCHIVE_DAYS} DAY)" \
  "${MYSQL_DB}" document > "${ARCHIVE_DIR}/${TIMESTAMP}/old_documents.sql" 2>/dev/null || true

# Export old conversation sessions
mysqldump -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" \
  --single-transaction --where="create_time < DATE_SUB(NOW(), INTERVAL ${ARCHIVE_DAYS} DAY)" \
  "${MYSQL_DB}" conversation > "${ARCHIVE_DIR}/${TIMESTAMP}/old_conversations.sql" 2>/dev/null || true

# Compress
gzip "${ARCHIVE_DIR}/${TIMESTAMP}"/*.sql 2>/dev/null || true

# Upload to S3
if [[ -n "${S3_BUCKET}" ]] && command -v aws &>/dev/null; then
  echo "[$(date)] Uploading archive to S3..."
  aws s3 sync "${ARCHIVE_DIR}/${TIMESTAMP}/" "s3://${S3_BUCKET}/yourrag-archive/${TIMESTAMP}/"
  echo "[$(date)] S3 upload complete."
fi

TOTAL_SIZE=$(du -sh "${ARCHIVE_DIR}/${TIMESTAMP}" | cut -f1)
echo "[$(date)] Archive complete: ${ARCHIVE_DIR}/${TIMESTAMP} (${TOTAL_SIZE})"
echo "[$(date)] NOTE: Review archived data before deleting from the active database."
