#!/usr/bin/env bash
set -euo pipefail

ROLLBACK_IMAGE="${1:-${LZKB_ROLLBACK_IMAGE:-}}"
DEPLOY_DIR="${LZKB_DEPLOY_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_FILE="${LZKB_COMPOSE_FILE:-deploy/docker-compose.operational.yml}"
HEALTH_URL="${LZKB_RELEASE_URL:-}"

if [[ -z "${ROLLBACK_IMAGE}" ]]; then
  echo "Usage: $0 ghcr.io/however-yir/lzkb:<previous-tag>" >&2
  exit 2
fi

cd "${DEPLOY_DIR}"
export LZKB_IMAGE="${ROLLBACK_IMAGE}"

docker compose -f "${COMPOSE_FILE}" pull web worker scheduler local-model
docker compose -f "${COMPOSE_FILE}" up -d web worker scheduler local-model

if [[ -n "${HEALTH_URL}" ]]; then
  ./scripts/post-release-healthcheck.sh "${HEALTH_URL}"
fi

echo "Rollback completed with image: ${ROLLBACK_IMAGE}"
