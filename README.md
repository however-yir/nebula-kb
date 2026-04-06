# LZKB

LZKB is a self-hosted enterprise agent and knowledge base platform maintained as a customized fork for private deployment and secondary development.

## Why This Fork

This repository is maintained for:
- building an internal AI knowledge assistant for private data;
- customizing model routing and tool workflows for business scenarios;
- reducing upstream brand coupling in docs, defaults, and runtime naming;
- creating a stable base for long-term independent iteration.

## What Has Been Customized

### 1) Naming and namespace
- Backend Django namespace migrated from `maxkb` to `lzkb`.
- Runtime settings module now uses `lzkb.settings`.
- Frontend global object migrated from `window.MaxKB` to `window.LZKB`.
- Locale persistence key migrated from `MaxKB-locale` to `LZKB-locale`.
- Frontend default title changed to `LZKB`.

### 2) Secure configuration defaults
- Sensitive defaults are replaced with placeholders:
  - `CHANGE_ME_DB_PASSWORD`
  - `CHANGE_ME_REDIS_PASSWORD`
- Built-in default user password changed to `ChangeMe@1234!` (must be overridden in production).
- Added startup guard in `installer/start-all.sh` to block placeholder secrets.

### 3) Configuration templates
- Added root [`config_example.yml`](./config_example.yml) for file-based configuration.
- Added root [`.env.example`](./.env.example) for environment-based configuration.
- Preferred env prefix is `LZKB_`, while `MAXKB_` remains compatible for existing deployments.

### 4) Branding and links
- Replaced major visible project identity references in frontend defaults and docs.
- Project URLs in UI defaults now point to your fork placeholders.

## Quick Start (Docker)

```bash
docker run -d \
  --name=lzkb \
  --restart=always \
  -p 8080:8080 \
  -e POSTGRES_PASSWORD='your-strong-postgres-password' \
  -e REDIS_PASSWORD='your-strong-redis-password' \
  -e LZKB_CONFIG_TYPE=ENV \
  -e LZKB_DB_NAME=lzkb \
  -e LZKB_DB_HOST=127.0.0.1 \
  -e LZKB_DB_PORT=5432 \
  -e LZKB_DB_USER=root \
  -e LZKB_DB_PASSWORD='your-strong-postgres-password' \
  -e LZKB_REDIS_HOST=127.0.0.1 \
  -e LZKB_REDIS_PORT=6379 \
  -e LZKB_REDIS_PASSWORD='your-strong-redis-password' \
  -v ~/.lzkb:/opt/maxkb \
  your-dockerhub-or-registry/lzkb:latest
```

Then open:

- Admin: `http://<your-host>:8080/admin`
- Chat: `http://<your-host>:8080/chat`

## Local Development

### Backend

```bash
# from repo root
python -m uv pip install -r pyproject.toml
python apps/manage.py migrate
python main.py dev web
```

### Frontend

```bash
cd ui
npm install
npm run dev
```

## Difference from Upstream

Compared with upstream MaxKB, this fork currently focuses on:
- namespace decoupling (`maxkb` -> `lzkb` for core runtime package);
- security hardening for default credentials and startup checks;
- project identity replacement in UI/runtime defaults;
- fork-oriented documentation and deployment entrypoints.

Future roadmap in this fork:
- deeper business module refactor by domain boundaries;
- provider abstraction and plugin governance;
- CI enhancement (tests, quality gates, dependency locks);
- full GitHub metadata and brand asset replacement.

## Repository Metadata (GitHub)

Suggested repository description:

> LZKB - Self-hosted enterprise agent and knowledge base platform for private deployment and custom AI workflows.

Suggested Topics:

`rag`, `agent`, `knowledge-base`, `django`, `vue`, `langchain`, `llm`, `self-hosted`, `enterprise-ai`, `workflow`

## License

This project is a fork based on GPLv3-licensed upstream work and remains under GPLv3 obligations.

See:
- [LICENSE](./LICENSE)
- [NOTICE-LZKB.md](./NOTICE-LZKB.md)
