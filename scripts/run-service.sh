#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-web}"

export PYTHONPATH="${ROOT_DIR}/apps:${PYTHONPATH:-}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-lzkb.settings}"

health_pid=""

start_health_sidecar() {
  local port="${1}"
  export LZKB_HEALTH_PORT="${port}"
  python -m ops.health_http --role "${ROLE}" --port "${port}" &
  health_pid="$!"
}

cleanup() {
  if [[ -n "${health_pid}" ]]; then
    kill "${health_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

case "${ROLE}" in
  web)
    export SERVER_NAME=web
    exec python "${ROOT_DIR}/main.py" start web
    ;;
  worker|task)
    export SERVER_NAME=worker
    start_health_sidecar "${LZKB_HEALTH_PORT:-8081}"
    python "${ROOT_DIR}/main.py" start worker
    ;;
  scheduler)
    export SERVER_NAME=scheduler
    export ENABLE_SCHEDULER=1
    exec python "${ROOT_DIR}/main.py" start scheduler
    ;;
  model|local_model)
    export SERVER_NAME=local_model
    exec python "${ROOT_DIR}/main.py" start local_model
    ;;
  all)
    exec python "${ROOT_DIR}/main.py" start all
    ;;
  *)
    echo "Unknown LZKB service role: ${ROLE}" >&2
    exit 2
    ;;
esac
