#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON="${PYTHON_BIN}"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "python or python3 is required." >&2
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-${ROOT_DIR}/apps}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-nebula.settings.test}"
export NEBULA_CONFIG_TYPE="${NEBULA_CONFIG_TYPE:-${LZKB_CONFIG_TYPE:-ENV}}"
export NEBULA_DATA_DIR="${NEBULA_DATA_DIR:-${LZKB_DATA_DIR:-/tmp/nebula-quality-data}}"
export NEBULA_DB_NAME="${NEBULA_DB_NAME:-${LZKB_DB_NAME:-/tmp/nebula-quality.sqlite3}}"
export NEBULA_DB_HOST="${NEBULA_DB_HOST:-${LZKB_DB_HOST:-127.0.0.1}}"
export NEBULA_DB_PORT="${NEBULA_DB_PORT:-${LZKB_DB_PORT:-5432}}"
export NEBULA_DB_USER="${NEBULA_DB_USER:-${LZKB_DB_USER:-root}}"
export NEBULA_DB_PASSWORD="${NEBULA_DB_PASSWORD:-${LZKB_DB_PASSWORD:-test-password}}"
export NEBULA_DB_ENGINE="${NEBULA_DB_ENGINE:-${LZKB_DB_ENGINE:-django.db.backends.sqlite3}}"
export NEBULA_DB_MAX_OVERFLOW="${NEBULA_DB_MAX_OVERFLOW:-${LZKB_DB_MAX_OVERFLOW:-10}}"
export NEBULA_REDIS_HOST="${NEBULA_REDIS_HOST:-${LZKB_REDIS_HOST:-127.0.0.1}}"
export NEBULA_REDIS_PORT="${NEBULA_REDIS_PORT:-${LZKB_REDIS_PORT:-6379}}"
export NEBULA_REDIS_PASSWORD="${NEBULA_REDIS_PASSWORD:-${LZKB_REDIS_PASSWORD:-test-password}}"
export NEBULA_REDIS_DB="${NEBULA_REDIS_DB:-${LZKB_REDIS_DB:-0}}"
export NEBULA_REDIS_MAX_CONNECTIONS="${NEBULA_REDIS_MAX_CONNECTIONS:-${LZKB_REDIS_MAX_CONNECTIONS:-10}}"
export NEBULA_ENABLE_FORCE_GC="${NEBULA_ENABLE_FORCE_GC:-${LZKB_ENABLE_FORCE_GC:-0}}"
export NEBULA_LANGUAGE_CODE="${NEBULA_LANGUAGE_CODE:-${LZKB_LANGUAGE_CODE:-zh-CN}}"
export NEBULA_TIME_ZONE="${NEBULA_TIME_ZONE:-${LZKB_TIME_ZONE:-Asia/Shanghai}}"

# LZKB_* fallback bridge for existing code paths.
export LZKB_CONFIG_TYPE="${LZKB_CONFIG_TYPE:-${NEBULA_CONFIG_TYPE}}"
export LZKB_DATA_DIR="${LZKB_DATA_DIR:-${NEBULA_DATA_DIR}}"
export LZKB_DB_NAME="${LZKB_DB_NAME:-${NEBULA_DB_NAME}}"
export LZKB_DB_HOST="${LZKB_DB_HOST:-${NEBULA_DB_HOST}}"
export LZKB_DB_PORT="${LZKB_DB_PORT:-${NEBULA_DB_PORT}}"
export LZKB_DB_USER="${LZKB_DB_USER:-${NEBULA_DB_USER}}"
export LZKB_DB_PASSWORD="${LZKB_DB_PASSWORD:-${NEBULA_DB_PASSWORD}}"
export LZKB_DB_ENGINE="${LZKB_DB_ENGINE:-${NEBULA_DB_ENGINE}}"
export LZKB_DB_MAX_OVERFLOW="${LZKB_DB_MAX_OVERFLOW:-${NEBULA_DB_MAX_OVERFLOW}}"
export LZKB_REDIS_HOST="${LZKB_REDIS_HOST:-${NEBULA_REDIS_HOST}}"
export LZKB_REDIS_PORT="${LZKB_REDIS_PORT:-${NEBULA_REDIS_PORT}}"
export LZKB_REDIS_PASSWORD="${LZKB_REDIS_PASSWORD:-${NEBULA_REDIS_PASSWORD}}"
export LZKB_REDIS_DB="${LZKB_REDIS_DB:-${NEBULA_REDIS_DB}}"
export LZKB_REDIS_MAX_CONNECTIONS="${LZKB_REDIS_MAX_CONNECTIONS:-${NEBULA_REDIS_MAX_CONNECTIONS}}"
export LZKB_ENABLE_FORCE_GC="${LZKB_ENABLE_FORCE_GC:-${NEBULA_ENABLE_FORCE_GC}}"
export LZKB_LANGUAGE_CODE="${LZKB_LANGUAGE_CODE:-${NEBULA_LANGUAGE_CODE}}"
export LZKB_TIME_ZONE="${LZKB_TIME_ZONE:-${NEBULA_TIME_ZONE}}"

COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-40}"
CORE_COVERAGE_SOURCE="${CORE_COVERAGE_SOURCE:-apps/users,apps/chat,apps/knowledge,apps/tools,apps/application,apps/system_manage}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/quality-gate.sh [gate ...]

Gates:
  smoke        Django configuration and repository smoke check
  unit         Unit tests for auth/token/tool logic
  integration  Integration tests for login, retrieval, and tool connection
  api          API regression surface for chat and application modules
  auth         Authentication and token regression tests
  permission   Permission module regression/import checks
  coverage     Coverage gate for high-risk modules
  release      Run the fixed release gate set
  all          Run smoke, unit, integration, api, auth, permission, coverage

Environment:
  PYTHON_BIN              Python executable override
  COVERAGE_FAIL_UNDER     Coverage threshold, default 40
  CORE_COVERAGE_SOURCE    Comma-separated coverage source paths
USAGE
}

run_manage() {
  (cd "${ROOT_DIR}" && "${PYTHON}" apps/manage.py "$@")
}

run_django_tests() {
  local name="$1"
  shift
  echo "==> ${name}"
  run_manage test "$@" --noinput --verbosity=2
}

run_smoke() {
  echo "==> smoke"
  run_manage check
  if "${PYTHON}" -m pytest --version >/dev/null 2>&1; then
    (cd "${ROOT_DIR}" && "${PYTHON}" -m pytest tests/test_smoke.py)
  else
    echo "pytest is not installed; skipping tests/test_smoke.py" >&2
  fi
}

run_unit() {
  run_django_tests "unit" users tools
}

run_integration() {
  run_django_tests "integration" \
    users.tests.LoginSerializerTests \
    knowledge.tests.KnowledgeRetrievalTests \
    tools.tests.ToolConnectionTests
}

run_api() {
  run_django_tests "api regression" chat application
}

run_auth() {
  run_django_tests "auth/token regression" users.tests.LoginSerializerTests
}

run_permission() {
  run_django_tests "permission regression" system_manage
}

run_coverage() {
  echo "==> coverage gate (${COVERAGE_FAIL_UNDER}%)"
  if ! "${PYTHON}" -m coverage --version >/dev/null 2>&1; then
    echo "coverage is required for the coverage gate." >&2
    exit 1
  fi

  (cd "${ROOT_DIR}" && \
    "${PYTHON}" -m coverage run --source="${CORE_COVERAGE_SOURCE}" -m django test \
      users chat knowledge tools application system_manage \
      --noinput --verbosity=1 && \
    "${PYTHON}" -m coverage xml -o coverage.xml && \
    "${PYTHON}" -m coverage report --fail-under="${COVERAGE_FAIL_UNDER}")
}

run_release() {
  run_smoke
  run_api
  run_auth
  run_permission
  run_coverage
}

if [[ $# -eq 0 ]]; then
  set -- all
fi

for gate in "$@"; do
  case "${gate}" in
    -h|--help)
      usage
      exit 0
      ;;
    smoke)
      run_smoke
      ;;
    unit)
      run_unit
      ;;
    integration)
      run_integration
      ;;
    api)
      run_api
      ;;
    auth)
      run_auth
      ;;
    permission)
      run_permission
      ;;
    coverage)
      run_coverage
      ;;
    release)
      run_release
      ;;
    all)
      run_smoke
      run_unit
      run_integration
      run_api
      run_auth
      run_permission
      run_coverage
      ;;
    *)
      echo "Unknown gate: ${gate}" >&2
      usage
      exit 1
      ;;
  esac
done
