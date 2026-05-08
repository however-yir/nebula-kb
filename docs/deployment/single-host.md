# Single Host Deployment

## 1. Prerequisites

- Linux host with Docker and Docker Compose installed
- At least 8 CPU / 16 GB RAM (recommended)
- Open ports: `80`, `443`, `9380`, `9381`

## 2. Prepare configuration

```bash
cd docker
cp .env .env.local
```

Update at minimum:

- `MYSQL_PASSWORD`
- `REDIS_PASSWORD`
- `MINIO_PASSWORD`
- `ELASTIC_PASSWORD` or `OPENSEARCH_PASSWORD`
- `DEFAULT_SUPERUSER_EMAIL`
- `DEFAULT_SUPERUSER_PASSWORD`

Disable public signup for production:

```bash
REGISTER_ENABLED=0
```

## 3. Optional RSA key pair

```bash
cd ..
./tools/scripts/generate_rsa_keys.sh
```

Then export generated values (or place them in your runtime secrets manager):

- `YOURRAG_RSA_PRIVATE_KEY_PATH`
- `YOURRAG_RSA_PUBLIC_KEY_PATH`
- `YOURRAG_RSA_KEY_PASSPHRASE`

## 4. Start services

```bash
cd docker
docker compose --env-file .env.local -f docker-compose.yml up -d
```

## 5. Verify

```bash
docker compose -f docker-compose.yml ps
curl -f http://127.0.0.1:9380/v1/system/ping
```
