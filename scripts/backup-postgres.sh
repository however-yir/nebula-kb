#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${NEBULA_BACKUP_DIR:-${LZKB_BACKUP_DIR:-${ROOT_DIR}/backups/postgres}}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_FILE="${1:-${BACKUP_DIR}/nebula-${TIMESTAMP}.dump}"

if [[ -n "${DATABASE_URL_FILE:-}" && -f "${DATABASE_URL_FILE}" ]]; then
  DATABASE_URL="$(<"${DATABASE_URL_FILE}")"
fi

mkdir -p "$(dirname "${OUTPUT_FILE}")"
chmod 700 "$(dirname "${OUTPUT_FILE}")"

if [[ -n "${DATABASE_URL:-}" ]]; then
  pg_dump --format=custom --no-owner --file="${OUTPUT_FILE}" "${DATABASE_URL}"
else
  export PGPASSWORD="${NEBULA_DB_PASSWORD:-${LZKB_DB_PASSWORD:-${POSTGRES_PASSWORD:-}}}"
  pg_dump \
    --format=custom \
    --no-owner \
    --host="${NEBULA_DB_HOST:-${LZKB_DB_HOST:-127.0.0.1}}" \
    --port="${NEBULA_DB_PORT:-${LZKB_DB_PORT:-5432}}" \
    --username="${NEBULA_DB_USER:-${LZKB_DB_USER:-root}}" \
    --dbname="${NEBULA_DB_NAME:-${LZKB_DB_NAME:-nebula}}" \
    --file="${OUTPUT_FILE}"
fi

sha256sum "${OUTPUT_FILE}" > "${OUTPUT_FILE}.sha256"
echo "PostgreSQL backup created: ${OUTPUT_FILE}"
