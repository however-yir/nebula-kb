# PgBouncer Setup Guide

## Overview
PgBouncer provides connection pooling at the protocol level, reducing PostgreSQL connection overhead for NebulaKB.

## Configuration

### Docker Compose (recommended)
PgBouncer is included in `deploy/docker-compose.operational.yml`. Set these env vars:

```env
NEBULA_DB_USE_PGBOUNCER=true
NEBULA_DB_HOST=pgbouncer
NEBULA_DB_PGBOUNCER_PORT=6432
```

### Pool Mode
Use **transaction** mode for best compatibility with Django:
```
pool_mode = transaction
default_pool_size = 20
max_client_conn = 200
```

### Tuning
- `default_pool_size`: Match your `DB_POOL_SIZE` setting (default 20)
- `max_client_conn`: Should exceed sum of all app pool sizes
- PostgreSQL `max_connections`: Should be > PgBouncer `default_pool_size` * number of databases

## Troubleshooting
- If `SET` commands fail, ensure `server_reset_query = DISCARD ALL`
- Prepared statements require PgBouncer 1.21+ with `prepared statement caching`
