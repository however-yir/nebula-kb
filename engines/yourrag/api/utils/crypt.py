#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import base64
import os
import sys
from pathlib import Path
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from common.file_utils import get_project_base_directory


LEGACY_KEY_PASSPHRASE = "Welcome"


def _resolve_key_path(kind: str) -> str:
    env_names = (
        f"YOURRAG_RSA_{kind.upper()}_KEY_PATH",
        f"RAGFLOW_RSA_{kind.upper()}_KEY_PATH",
    )
    for env_name in env_names:
        env_path = os.environ.get(env_name, "").strip()
        if env_path:
            return env_path
    return os.path.join(get_project_base_directory(), "conf", f"{kind}.pem")


def _passphrase_candidates():
    candidates = []
    for env_name in ("YOURRAG_RSA_KEY_PASSPHRASE", "RAGFLOW_RSA_KEY_PASSPHRASE"):
        value = os.environ.get(env_name, "")
        if value:
            candidates.append(value)
    candidates.append(None)
    candidates.append(LEGACY_KEY_PASSPHRASE)

    deduplicated = []
    for value in candidates:
        if value not in deduplicated:
            deduplicated.append(value)
    return deduplicated


def _load_rsa_key(path: str):
    pem = Path(path).read_text()
    last_error = None
    for passphrase in _passphrase_candidates():
        try:
            return RSA.importKey(pem, passphrase)
        except (ValueError, TypeError, IndexError) as exc:
            last_error = exc
    raise ValueError(f"unable to load RSA key from {path}: {last_error}")


def _is_base64_utf8(value: str) -> bool:
    try:
        decoded = base64.b64decode(value, validate=True)
        decoded.decode("utf-8")
        return True
    except Exception:
        return False


def _to_base64_utf8(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def crypt(line):
    """
    decrypt(crypt(input_string)) == base64(input_string), which frontend and ragflow_cli use.
    """
    password_base64 = base64.b64encode(line.encode('utf-8')).decode("utf-8")
    public_key_path = _resolve_key_path("public")
    try:
        rsa_key = _load_rsa_key(public_key_path)
        cipher = Cipher_pkcs1_v1_5.new(rsa_key)
        encrypted_password = cipher.encrypt(password_base64.encode())
        return base64.b64encode(encrypted_password).decode('utf-8')
    except Exception:
        # Fallback: transport as base64-only when RSA key files are unavailable.
        return password_base64


def decrypt(line):
    private_key_path = _resolve_key_path("private")
    try:
        rsa_key = _load_rsa_key(private_key_path)
        cipher = Cipher_pkcs1_v1_5.new(rsa_key)
        failed = b"Fail to decrypt password!"
        decrypted = cipher.decrypt(base64.b64decode(line), failed)
        if decrypted == failed:
            raise ValueError("RSA decrypt failed")
        return decrypted.decode("utf-8")
    except Exception:
        # If input is already base64(password), keep compatibility with existing hash flow.
        if _is_base64_utf8(line):
            return line
        # Last resort: treat incoming value as plain password.
        return _to_base64_utf8(line)


def decrypt2(crypt_text):
    from base64 import b64decode, b16decode
    from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
    try:
        decode_data = b64decode(crypt_text)
        if len(decode_data) == 127:
            hex_fixed = '00' + decode_data.hex()
            decode_data = b16decode(hex_fixed.upper())

        private_key_path = _resolve_key_path("private")
        rsa_key = _load_rsa_key(private_key_path)
        cipher = Cipher_PKCS1_v1_5.new(rsa_key)
        decrypt_text = cipher.decrypt(decode_data, None)
        return (b64decode(decrypt_text)).decode()
    except Exception:
        if _is_base64_utf8(crypt_text):
            return b64decode(crypt_text).decode("utf-8")
        raise


if __name__ == "__main__":
    passwd = crypt(sys.argv[1])
    print(passwd)
    print(decrypt(passwd))
