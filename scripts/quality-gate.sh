#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON="${PYTHON_BIN}"
elif [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON="${ROOT_DIR}/.venv/bin/python"
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

COVERAGE_FAIL_UNDER="${COVERAGE_FAIL_UNDER:-44}"
CORE_COVERAGE_SOURCE="${CORE_COVERAGE_SOURCE:-apps/users,apps/chat,apps/knowledge,apps/tools,apps/application,apps/system_manage}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/quality-gate.sh [gate ...]

Gates:
  smoke              Django configuration and repository smoke check
  unit               Unit tests for auth/token/tool logic
  integration        Integration tests for login, retrieval, and tool connection
  api                API regression surface for chat and application modules
  auth               Authentication and token regression tests
  permission         Permission module regression/import checks
  coverage           Coverage gate for high-risk modules
  frontend-lint      Frontend ESLint check
  frontend-typecheck Frontend TypeScript type check
  frontend-test      Frontend vitest tests
  completion         Functional completion roadmap integrity check
  lifecycle-demo     Knowledge asset lifecycle demo regression
  application-workflow-demo Feedback, dashboard, application, and workflow demo regression
  platform-governance-demo Model/tool/trigger/permission/audit demo regression
  local-readiness-docs Local startup/configuration documentation drift check
  release            Run the fixed release gate set
  all                Run smoke, unit, integration, api, auth, permission, coverage, frontend, docs gates

Environment:
  PYTHON_BIN              Python executable override
  COVERAGE_FAIL_UNDER     Coverage threshold, default 44
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

run_frontend_lint() {
  echo "==> frontend-lint"
  (cd "${ROOT_DIR}/ui" && npm run lint)
}

run_frontend_typecheck() {
  echo "==> frontend-typecheck"
  (cd "${ROOT_DIR}/ui" && npm run type-check)
}

run_frontend_test() {
  echo "==> frontend-test"
  (cd "${ROOT_DIR}/ui" && npm test)
}

run_completion() {
  echo "==> completion roadmap"
  local roadmap="${ROOT_DIR}/docs/quality/functional-completion-roadmap.md"
  local checklist="${ROOT_DIR}/docs/quality/release-checklist.md"
  local count

  if [[ ! -f "${roadmap}" ]]; then
    echo "Missing completion roadmap: ${roadmap}" >&2
    exit 1
  fi

  count="$(grep -E '^[0-9]{3}\. P[0-2] ' "${roadmap}" | wc -l | tr -d ' ')"
  if [[ "${count}" != "300" ]]; then
    echo "Expected 300 completion items, found ${count}." >&2
    exit 1
  fi

  grep -q '^001\. P0 ' "${roadmap}"
  grep -q '^300\. P[0-2] ' "${roadmap}"
  grep -q 'functional-completion-roadmap.md' "${checklist}"
}

run_lifecycle_demo() {
  echo "==> lifecycle-demo"
  local output
  output="$(mktemp)"

  (cd "${ROOT_DIR}" && "${PYTHON}" scripts/demo_lifecycle.py > "${output}")
  grep -q 'NebulaKB demo: knowledge asset lifecycle' "${output}"
  grep -q 'status=indexed' "${output}"
  grep -q 'Upload progress: 100%' "${output}"
  grep -q 'Status path: waiting -> uploading -> uploaded -> parsing -> parsed -> indexing -> indexed' "${output}"
  grep -q 'Chunk preview:' "${output}"
  grep -q 'Keyword hit:' "${output}"
  grep -q 'Vector hit:' "${output}"
  grep -q 'Score:' "${output}"
  grep -q 'Citation locator:' "${output}"
  grep -q 'Source locator:' "${output}"
  grep -q 'Stream state: completed' "${output}"
  grep -q 'Fallback: empty_result' "${output}"
  grep -q '"knowledge_hit_rate": 0.75' "${output}"
  grep -q '"low_quality_answer_rate": 1.0' "${output}"
  grep -q 'Knowledge-base health dashboard' "${output}"
  grep -q '"health_score":' "${output}"
  grep -q '"status": "closed"' "${output}"
  rm -f "${output}"
}

run_application_workflow_demo() {
  echo "==> application-workflow-demo"
  local output
  output="$(mktemp)"

  (cd "${ROOT_DIR}" && "${PYTHON}" scripts/demo_application_workflow.py > "${output}")
  grep -q 'NebulaKB demo: feedback, dashboard, application workflow' "${output}"
  grep -q 'Thumbs up feedback: rating=5' "${output}"
  grep -q 'Thumbs down feedback: rating=1' "${output}"
  grep -q 'Governance task:' "${output}"
  grep -q 'Operations dashboard first screen:' "${output}"
  grep -q '"summary_cards"' "${output}"
  grep -q 'Application created: simple' "${output}"
  grep -q 'Application created: workflow' "${output}"
  grep -q 'Published version: 1' "${output}"
  grep -q 'API key: nebula_' "${output}"
  grep -q 'Workflow node docs:' "${output}"
  grep -q 'Connection validation: ok' "${output}"
  grep -q 'Condition test: true' "${output}"
  grep -q 'Workflow debug status: success' "${output}"
  grep -q 'Run log events:' "${output}"
  grep -q 'workflow_completed' "${output}"
  rm -f "${output}"
}

run_platform_governance_demo() {
  echo "==> platform-governance-demo"
  local output
  output="$(mktemp)"

  (cd "${ROOT_DIR}" && "${PYTHON}" scripts/demo_platform_governance.py > "${output}")
  grep -q 'NebulaKB demo: platform governance' "${output}"
  grep -q 'Model provider onboarded:' "${output}"
  grep -q 'Model connection: ok' "${output}"
  grep -q 'Embedding test dimension:' "${output}"
  grep -q 'Default model:' "${output}"
  grep -q 'is_default=True' "${output}"
  grep -q 'Tool debug: success' "${output}"
  grep -q 'Tool permissions:' "${output}"
  grep -q 'Tool schema: input=' "${output}"
  grep -q 'Trigger enabled: True' "${output}"
  grep -q 'Trigger target validated:' "${output}"
  grep -q 'Trigger run count: 1' "${output}"
  grep -q 'Permission matrix:' "${output}"
  grep -q 'Resource authorization:' "${output}"
  grep -q 'Workspace isolation blocked: true' "${output}"
  grep -q 'User disabled:' "${output}"
  grep -q 'SSO configured: oidc, enabled=True' "${output}"
  grep -q 'Audit summary:' "${output}"
  grep -Fq '"api_key": "********"' "${output}"
  grep -Fq '"token": "********"' "${output}"
  rm -f "${output}"
}

run_local_readiness_docs() {
  echo "==> local-readiness-docs"
  local readme="${ROOT_DIR}/README.md"
  local readme_cn="${ROOT_DIR}/README_CN.md"
  local ops="${ROOT_DIR}/docs/ops/operability.md"
  local env_example="${ROOT_DIR}/.env.example"

  for file in "${readme}" "${readme_cn}" "${ops}" "${env_example}"; do
    if [[ ! -f "${file}" ]]; then
      echo "Missing local readiness documentation asset: ${file}" >&2
      exit 1
    fi
  done

  grep -Fq '### 首次启动检查清单' "${readme}"
  grep -Fq '### 首次启动检查清单' "${readme_cn}"
  grep -Fq 'docs/ops/operability.md#本地启动排查矩阵' "${readme}"
  grep -Fq '## 本地启动排查矩阵' "${ops}"
  grep -Fq '## 本地数据目录与持久化' "${ops}"
  grep -Fq 'docker compose --env-file .env -f docker-compose.dev.yml ps' "${ops}"
  grep -Fq 'CREATE EXTENSION IF NOT EXISTS vector;' "${ops}"
  grep -Fq 'NEBULA_DATA_DIR=/tmp/nebula' "${env_example}"
  grep -Fq 'Security defaults:' "${env_example}"
  grep -Fq 'DATABASE_URL=postgresql://' "${env_example}"
  grep -Fq 'REDIS_URL=redis://' "${env_example}"
}

run_release() {
  run_completion
  run_lifecycle_demo
  run_application_workflow_demo
  run_platform_governance_demo
  run_local_readiness_docs
  run_smoke
  run_api
  run_auth
  run_permission
  run_coverage
  run_frontend_lint
  run_frontend_typecheck
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
    frontend-lint)
      run_frontend_lint
      ;;
    frontend-typecheck)
      run_frontend_typecheck
      ;;
    frontend-test)
      run_frontend_test
      ;;
    completion)
      run_completion
      ;;
    lifecycle-demo)
      run_lifecycle_demo
      ;;
    application-workflow-demo)
      run_application_workflow_demo
      ;;
    platform-governance-demo)
      run_platform_governance_demo
      ;;
    local-readiness-docs)
      run_local_readiness_docs
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
      run_frontend_lint
      run_frontend_typecheck
      run_frontend_test
      run_completion
      run_lifecycle_demo
      run_application_workflow_demo
      run_platform_governance_demo
      run_local_readiness_docs
      ;;
    *)
      echo "Unknown gate: ${gate}" >&2
      usage
      exit 1
      ;;
  esac
done
