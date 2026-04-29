# NebulaKB Demo GIF Recording

This guide records a short browser demo for the README hero.

## Prerequisites

- PostgreSQL is running and the `lzkb` database has the `vector` extension.
- Redis is running with the password from `.env` (`LZKB_REDIS_PASSWORD`).
- Django is available at `http://localhost:8080`.
- ImageMagick is installed and exposes the `magick` command.
- Playwright is installed in a local or temporary Node package directory.

## Start The App

```bash
set -a
source .env
set +a
export NEBULA_DATA_DIR=/tmp/nebula-data
export LZKB_DATA_DIR=/tmp/nebula-data
./scripts/demo_lifecycle.py
.venv/bin/python main.py dev web
curl -s http://localhost:8080/healthz
```

## Install Playwright Without Touching The Repo

```bash
mkdir -p /tmp/nebula-playwright
npm install --prefix /tmp/nebula-playwright --no-save playwright
```

## Record

```bash
PLAYWRIGHT_REQUIRE_ROOT=/tmp/nebula-playwright \
PLAYWRIGHT_CHROMIUM_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
node scripts/record_demo_gif.mjs
```

The script captures six frames and writes:

```text
docs/assets/screenshots/demo.gif
```

Frame PNG files are written to `tmp/demo-gif-frames/`, which is ignored by git.
