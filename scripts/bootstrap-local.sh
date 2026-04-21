#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.dev.yml"
WITH_OLLAMA=0
START_STACK=0
PG_READY_RETRIES=30

compose_cmd() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

wait_for_postgres() {
  local attempt=1
  until compose_cmd exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
    if [[ "${attempt}" -ge "${PG_READY_RETRIES}" ]]; then
      echo "PostgreSQL did not become ready after ${PG_READY_RETRIES} attempts." >&2
      return 1
    fi
    sleep 2
    attempt=$((attempt + 1))
  done
}

ensure_pgvector_extension() {
  compose_cmd exec -T postgres sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"' \
    >/dev/null
}

usage() {
  cat <<'USAGE'
Usage: ./scripts/bootstrap-local.sh [--with-ollama] [--start]

Options:
  --with-ollama  Start Ollama container in addition to PostgreSQL and Redis
  --start        Start dependency stack after environment checks
  -h, --help     Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-ollama)
      WITH_OLLAMA=1
      shift
      ;;
    --start)
      START_STACK=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  echo "Created ${ENV_FILE} from template."
fi

if grep -Eq 'CHANGE_ME_' "${ENV_FILE}"; then
  echo "Detected placeholder secrets in ${ENV_FILE}. Please update passwords before running." >&2
  exit 1
fi

if [[ "${START_STACK}" -eq 1 ]]; then
  services=(postgres redis)
  if [[ "${WITH_OLLAMA}" -eq 1 ]]; then
    services+=(ollama)
  fi
  compose_cmd up -d "${services[@]}"
  wait_for_postgres
  ensure_pgvector_extension
  echo "Dependencies are up: ${services[*]}"
  echo "pgvector extension ensured in ${LZKB_DB_NAME:-lzkb}."
fi

cat <<'NEXT'
Next steps:
  1) python -m venv .venv && source .venv/bin/activate
  2) pip install -U pip && pip install -e .
  3) python apps/manage.py migrate
  4) python main.py dev web
NEXT
