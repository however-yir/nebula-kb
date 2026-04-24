#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${NEBULA_RELEASE_URL:-${LZKB_RELEASE_URL:-}}}"
TIMEOUT_SECONDS="${NEBULA_HEALTHCHECK_TIMEOUT_SECONDS:-${LZKB_HEALTHCHECK_TIMEOUT_SECONDS:-180}}"
INTERVAL_SECONDS="${NEBULA_HEALTHCHECK_INTERVAL_SECONDS:-${LZKB_HEALTHCHECK_INTERVAL_SECONDS:-5}}"

if [[ -z "${BASE_URL}" ]]; then
  echo "Usage: $0 https://nebulakb.example.com" >&2
  exit 2
fi

BASE_URL="${BASE_URL%/}"
deadline=$((SECONDS + TIMEOUT_SECONDS))

while (( SECONDS < deadline )); do
  if curl -fsS "${BASE_URL}/healthz" >/dev/null && curl -fsS "${BASE_URL}/readyz" >/dev/null; then
    echo "Release health check passed: ${BASE_URL}"
    exit 0
  fi
  sleep "${INTERVAL_SECONDS}"
done

echo "Release health check failed after ${TIMEOUT_SECONDS}s: ${BASE_URL}" >&2
exit 1
