#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
WITH_OLLAMA=0
START_STACK=0

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
  docker compose --env-file "${ENV_FILE}" -f "${ROOT_DIR}/docker-compose.dev.yml" up -d "${services[@]}"
  echo "Dependencies are up: ${services[*]}"
fi

cat <<'NEXT'
Next steps:
  1) python -m venv .venv && source .venv/bin/activate
  2) pip install -U pip && pip install -e .
  3) python apps/manage.py migrate
  4) python main.py dev web
NEXT
