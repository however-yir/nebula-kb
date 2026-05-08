#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONF_DIR="${PROJECT_ROOT}/conf"

PRIVATE_KEY_PATH="${YOURRAG_RSA_PRIVATE_KEY_PATH:-${RAGFLOW_RSA_PRIVATE_KEY_PATH:-${CONF_DIR}/private.pem}}"
PUBLIC_KEY_PATH="${YOURRAG_RSA_PUBLIC_KEY_PATH:-${RAGFLOW_RSA_PUBLIC_KEY_PATH:-${CONF_DIR}/public.pem}}"
KEY_PASSPHRASE="${YOURRAG_RSA_KEY_PASSPHRASE:-${RAGFLOW_RSA_KEY_PASSPHRASE:-}}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required but not found in PATH."
  exit 1
fi

mkdir -p "$(dirname "${PRIVATE_KEY_PATH}")" "$(dirname "${PUBLIC_KEY_PATH}")"

if [[ -z "${KEY_PASSPHRASE}" ]]; then
  KEY_PASSPHRASE="$(openssl rand -base64 24 | tr -d '\n')"
  echo "Generated random RSA passphrase."
fi

openssl genrsa -aes256 -passout "pass:${KEY_PASSPHRASE}" -out "${PRIVATE_KEY_PATH}" 2048
openssl rsa -in "${PRIVATE_KEY_PATH}" -passin "pass:${KEY_PASSPHRASE}" -pubout -out "${PUBLIC_KEY_PATH}"

chmod 600 "${PRIVATE_KEY_PATH}"
chmod 644 "${PUBLIC_KEY_PATH}"

cat <<EOF
RSA key pair generated successfully.
  private key: ${PRIVATE_KEY_PATH}
  public key : ${PUBLIC_KEY_PATH}

Export these variables before starting services:
  export YOURRAG_RSA_PRIVATE_KEY_PATH="${PRIVATE_KEY_PATH}"
  export YOURRAG_RSA_PUBLIC_KEY_PATH="${PUBLIC_KEY_PATH}"
  export YOURRAG_RSA_KEY_PASSPHRASE="${KEY_PASSPHRASE}"

For web build-time RSA encryption, also set:
  export VITE_RSA_PUBLIC_KEY="\$(awk 'NF {sub(/\\r/, \"\"); printf \"%s\\\\n\", \$0;}' "${PUBLIC_KEY_PATH}")"
EOF
