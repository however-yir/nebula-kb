#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

EXCLUDES=(
  --glob '!web/package-lock.json'
  --glob '!uv.lock'
)

echo "[audit] scanning branding leftovers..."
RAGFLOW_COUNT=$(rg -n 'ragflow' "${EXCLUDES[@]}" | wc -l | tr -d ' ')
INFINIFLOW_COUNT=$(rg -n 'infiniflow' "${EXCLUDES[@]}" | wc -l | tr -d ' ')

echo "ragflow:    ${RAGFLOW_COUNT}"
echo "infiniflow: ${INFINIFLOW_COUNT}"

echo
rg -n 'ragflow|infiniflow' "${EXCLUDES[@]}" | head -n 200 || true

if [[ "${RAGFLOW_COUNT}" -eq 0 && "${INFINIFLOW_COUNT}" -eq 0 ]]; then
  echo "[audit] clean"
else
  echo "[audit] leftovers remain"
fi
