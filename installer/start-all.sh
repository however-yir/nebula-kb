#!/bin/bash

set -e

APP_NAME="${LZKB_APP_NAME:-${MAXKB_APP_NAME:-LZKB}}"
DB_HOST="${LZKB_DB_HOST:-${MAXKB_DB_HOST:-127.0.0.1}}"
REDIS_HOST="${LZKB_REDIS_HOST:-${MAXKB_REDIS_HOST:-127.0.0.1}}"

for secret_var in POSTGRES_PASSWORD REDIS_PASSWORD LZKB_DB_PASSWORD LZKB_REDIS_PASSWORD MAXKB_DB_PASSWORD MAXKB_REDIS_PASSWORD; do
  val="${!secret_var}"
  if [ -z "$val" ]; then
    continue
  fi
  if [[ "$val" == CHANGE_ME_* ]]; then
    echo -e "\033[1;31mFATAL ERROR: Please set a real value for ${secret_var} before startup.\033[0m"
    exit 1
  fi
done

if [ -f "/opt/maxkb/PG_VERSION" ] || [ -f "/var/lib/postgresql/data/PG_VERSION" ]; then
  # 如果是v1版本一键安装的的目录则退出
  echo -e "\033[1;31mFATAL ERROR: Upgrade from v1 to v2 is not supported.\033[0m"
  echo -e "\033[1;31mThe process will exit.\033[0m"
  exit 1
fi

if [ "$DB_HOST" = "127.0.0.1" ]; then
  echo -e "\033[1;32mPostgreSQL starting...\033[0m"
  /usr/bin/start-postgres.sh &
  postgres_pid=$!
  sleep 5
  wait-for-it 127.0.0.1:5432 --timeout=120 --strict -- echo -e "\033[1;32mPostgreSQL started.\033[0m"
fi

if [ "$REDIS_HOST" = "127.0.0.1" ]; then
  echo -e "\033[1;32mRedis starting...\033[0m"
  /usr/bin/start-redis.sh &
  redis_pid=$!
  sleep 5
  wait-for-it 127.0.0.1:6379 --timeout=60 --strict -- echo -e "\033[1;32mRedis started.\033[0m"
fi

echo -e "\033[1;32m${APP_NAME} starting...\033[0m"
/usr/bin/start-maxkb.sh &
maxkb_pid=$!
sleep 10
wait-for-it 127.0.0.1:8080 --timeout=180 --strict -- echo -e "\033[1;32m${APP_NAME} started.\033[0m"

wait -n
echo -e "\033[1;31mSystem is shutting down.\033[0m"
kill $postgres_pid $redis_pid $maxkb_pid 2>/dev/null
wait
