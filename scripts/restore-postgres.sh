#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
  echo "Usage: $0 /path/to/nebula-backup.dump" >&2
  exit 2
fi

if [[ -f "${BACKUP_FILE}.sha256" ]]; then
  sha256sum -c "${BACKUP_FILE}.sha256"
fi

if [[ "${NEBULA_RESTORE_CONFIRM:-${LZKB_RESTORE_CONFIRM:-}}" != "yes" ]]; then
  echo "Refusing to restore without NEBULA_RESTORE_CONFIRM=yes." >&2
  echo "This operation replaces database objects in the target database." >&2
  exit 3
fi

if [[ -n "${DATABASE_URL_FILE:-}" && -f "${DATABASE_URL_FILE}" ]]; then
  DATABASE_URL="$(<"${DATABASE_URL_FILE}")"
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  pg_restore --clean --if-exists --no-owner --dbname="${DATABASE_URL}" "${BACKUP_FILE}"
else
  export PGPASSWORD="${NEBULA_DB_PASSWORD:-${LZKB_DB_PASSWORD:-${POSTGRES_PASSWORD:-}}}"
  pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --host="${NEBULA_DB_HOST:-${LZKB_DB_HOST:-127.0.0.1}}" \
    --port="${NEBULA_DB_PORT:-${LZKB_DB_PORT:-5432}}" \
    --username="${NEBULA_DB_USER:-${LZKB_DB_USER:-root}}" \
    --dbname="${NEBULA_DB_NAME:-${LZKB_DB_NAME:-nebula}}" \
    "${BACKUP_FILE}"
fi

echo "PostgreSQL restore completed from: ${BACKUP_FILE}"
