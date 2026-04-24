#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WITH_OLLAMA=0

usage() {
  cat <<'USAGE'
Usage: ./scripts/quick-install-mac.sh [--with-ollama]

Options:
  --with-ollama  Start Ollama container in addition to PostgreSQL and Redis
  -h, --help     Show this help message
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-ollama)
      WITH_OLLAMA=1
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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS. Please use scripts/quick-install-win.ps1 on Windows." >&2
  exit 1
fi

for cmd in "${PYTHON_BIN}" docker; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
done

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required. Please install/upgrade Docker Desktop." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Please start Docker Desktop first." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  echo "Created ${ENV_FILE} from template."
fi

"${PYTHON_BIN}" - "${ENV_FILE}" <<'PY'
import secrets
import string
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
env = {}
order = []

for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env[key] = value
    order.append(key)


def random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def set_if_missing_or_placeholder(key: str, value_factory):
    value = env.get(key)
    if value is None or value.strip() == "" or "CHANGE_ME_" in value:
        env[key] = value_factory() if callable(value_factory) else value_factory
        if key not in order:
            order.append(key)


def get_env(primary, legacy=None, default=""):
    value = env.get(primary)
    if value:
        return value
    if legacy:
        value = env.get(legacy)
        if value:
            return value
    return default


def sync_legacy(primary, legacy):
    if primary not in env:
        return
    value = env.get(legacy)
    if value is None or value.strip() == "" or "CHANGE_ME_" in value:
        env[legacy] = env[primary]
        if legacy not in order:
            order.append(legacy)


db_password_before = get_env("NEBULA_DB_PASSWORD", "LZKB_DB_PASSWORD")
redis_password_before = get_env("NEBULA_REDIS_PASSWORD", "LZKB_REDIS_PASSWORD")

set_if_missing_or_placeholder("SECRET_KEY", lambda: secrets.token_urlsafe(48))
if "NEBULA_DB_PASSWORD" not in env and "LZKB_DB_PASSWORD" in env:
    env["NEBULA_DB_PASSWORD"] = env["LZKB_DB_PASSWORD"]
    order.append("NEBULA_DB_PASSWORD")
if "NEBULA_REDIS_PASSWORD" not in env and "LZKB_REDIS_PASSWORD" in env:
    env["NEBULA_REDIS_PASSWORD"] = env["LZKB_REDIS_PASSWORD"]
    order.append("NEBULA_REDIS_PASSWORD")
set_if_missing_or_placeholder("NEBULA_DB_PASSWORD", random_password)
set_if_missing_or_placeholder("NEBULA_REDIS_PASSWORD", random_password)
sync_legacy("NEBULA_DB_PASSWORD", "LZKB_DB_PASSWORD")
sync_legacy("NEBULA_REDIS_PASSWORD", "LZKB_REDIS_PASSWORD")

db_user = get_env("NEBULA_DB_USER", "LZKB_DB_USER", "root")
db_host = get_env("NEBULA_DB_HOST", "LZKB_DB_HOST", "127.0.0.1")
db_port = get_env("NEBULA_DB_PORT", "LZKB_DB_PORT", "5432")
db_name = get_env("NEBULA_DB_NAME", "LZKB_DB_NAME", "nebula")
redis_host = get_env("NEBULA_REDIS_HOST", "LZKB_REDIS_HOST", "127.0.0.1")
redis_port = get_env("NEBULA_REDIS_PORT", "LZKB_REDIS_PORT", "6379")
redis_db = get_env("NEBULA_REDIS_DB", "LZKB_REDIS_DB", "0")

db_url = f"postgresql://{db_user}:{env['NEBULA_DB_PASSWORD']}@{db_host}:{db_port}/{db_name}"
redis_url = f"redis://:{env['NEBULA_REDIS_PASSWORD']}@{redis_host}:{redis_port}/{redis_db}"

if "DATABASE_URL" not in env:
    env["DATABASE_URL"] = db_url
    order.append("DATABASE_URL")
elif "CHANGE_ME_DB_PASSWORD" in env["DATABASE_URL"] or (
    db_password_before
    and db_password_before in env["DATABASE_URL"]
    and env["NEBULA_DB_PASSWORD"] != db_password_before
):
    env["DATABASE_URL"] = db_url

if "REDIS_URL" not in env:
    env["REDIS_URL"] = redis_url
    order.append("REDIS_URL")
elif "CHANGE_ME_REDIS_PASSWORD" in env["REDIS_URL"] or (
    redis_password_before
    and redis_password_before in env["REDIS_URL"]
    and env["NEBULA_REDIS_PASSWORD"] != redis_password_before
):
    env["REDIS_URL"] = redis_url

output = []
seen = set()
for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("#") or "=" not in line:
        output.append(line)
        continue
    key = line.split("=", 1)[0]
    if key in env:
        output.append(f"{key}={env[key]}")
        seen.add(key)
    else:
        output.append(line)

for key in order:
    if key in env and key not in seen:
        output.append(f"{key}={env[key]}")
        seen.add(key)

path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
PY

cd "${ROOT_DIR}"

if [[ ! -x ".venv/bin/python" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi

.venv/bin/python -m pip install -U pip
.venv/bin/pip install -e .

if [[ "${WITH_OLLAMA}" -eq 1 ]]; then
  ./scripts/bootstrap-local.sh --start --with-ollama
else
  ./scripts/bootstrap-local.sh --start
fi

.venv/bin/python apps/manage.py migrate

cat <<'NEXT'
Quick install completed.

Run backend:
  source .venv/bin/activate
  python main.py dev web

Frontend dev server:
  cd ui
  npm install
  npm run dev
NEXT
