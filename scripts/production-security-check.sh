#!/usr/bin/env bash
set -euo pipefail

environment="${NEBULA_ENVIRONMENT:-${APP_ENV:-${NEBULA_ENV:-dev}}}"

echo "NebulaKB production security check"
echo "environment=${environment}"

if [[ "${environment}" != "prod" ]]; then
  echo "status=skipped non-production"
  echo "set NEBULA_ENVIRONMENT=prod to enforce production checks"
  exit 0
fi

missing=0

require_non_placeholder() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    echo "missing=${name}" >&2
    missing=1
    return
  fi
  if [[ "${value}" == *"CHANGE_ME"* || "${value}" == *"django-insecure"* ]]; then
    echo "placeholder=${name}" >&2
    missing=1
  fi
}

require_non_placeholder "SECRET_KEY"
require_non_placeholder "ALLOWED_HOSTS"

if [[ -z "${DATABASE_URL:-}" ]]; then
  require_non_placeholder "NEBULA_DB_PASSWORD"
else
  require_non_placeholder "DATABASE_URL"
fi

if [[ -z "${REDIS_URL:-}" ]]; then
  require_non_placeholder "NEBULA_REDIS_PASSWORD"
else
  require_non_placeholder "REDIS_URL"
fi

if [[ "${DEBUG:-${NEBULA_DEBUG:-false}}" == "true" ]]; then
  echo "debug=true is not allowed in production" >&2
  missing=1
fi

if [[ "${missing}" -ne 0 ]]; then
  echo "status=failed"
  exit 1
fi

echo "checks=secret_key,allowed_hosts,database,redis,debug"
echo "status=passed"
