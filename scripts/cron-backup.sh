#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_DIR="${NEBULA_BACKUP_DIR:-${LZKB_BACKUP_DIR:-${ROOT_DIR}/backups/postgres}}"
LOG_DIR="${ROOT_DIR}/.runtime/logs/backup"

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/backup-${TIMESTAMP}.log"

echo "=== Backup started at $(date) ===" | tee -a "${LOG_FILE}"
bash "${ROOT_DIR}/scripts/backup-postgres.sh" "${BACKUP_DIR}/nebula-${TIMESTAMP}.dump" 2>&1 | tee -a "${LOG_FILE}"

echo "=== Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days ===" | tee -a "${LOG_FILE}"
find "${BACKUP_DIR}" -name "nebula-*.dump" -mtime +"${BACKUP_RETENTION_DAYS}" -delete 2>&1 | tee -a "${LOG_FILE}"
find "${BACKUP_DIR}" -name "nebula-*.dump.sha256" -mtime +"${BACKUP_RETENTION_DAYS}" -delete 2>&1 | tee -a "${LOG_FILE}"

echo "=== Backup completed at $(date) ===" | tee -a "${LOG_FILE}"
