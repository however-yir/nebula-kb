#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
  echo "Usage: $0 /path/to/lzkb-backup.dump" >&2
  exit 2
fi

if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

if [[ "${LZKB_RESTORE_CONFIRM:-}" != "yes" ]]; then
  echo "Refusing to restore without LZKB_RESTORE_CONFIRM=yes." >&2
  echo "This operation replaces database objects in the target database." >&2
  exit 3
fi

if [[ -n "${DATABASE_URL_FILE:-}" && -f "${DATABASE_URL_FILE}" ]]; then
  DATABASE_URL="$(<"${DATABASE_URL_FILE}")"
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  pg_restore --clean --if-exists --no-owner --dbname="${DATABASE_URL}" "${BACKUP_FILE}"
else
  export PGPASSWORD="${LZKB_DB_PASSWORD:-${POSTGRES_PASSWORD:-}}"
  pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --host="${LZKB_DB_HOST:-127.0.0.1}" \
    --port="${LZKB_DB_PORT:-5432}" \
    --username="${LZKB_DB_USER:-root}" \
    --dbname="${LZKB_DB_NAME:-lzkb}" \
    "${BACKUP_FILE}"
fi

echo "PostgreSQL restore completed from: ${BACKUP_FILE}"
