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

from http_client import HttpClient
import os
import base64
from pathlib import Path


class AuthException(Exception):
    def __init__(self, message, code=401):
        super().__init__(message)
        self.code = code
        self.message = message


def encrypt_password(password_plain: str) -> str:
    password_base64 = base64.b64encode(password_plain.encode("utf-8")).decode("utf-8")

    # Allow no-RSA mode (transport plain base64 only).
    public_key_pem = os.environ.get("YOURRAG_RSA_PUBLIC_KEY_PEM") or os.environ.get("RAGFLOW_RSA_PUBLIC_KEY_PEM")
    if not public_key_pem:
        for env_name in ("YOURRAG_RSA_PUBLIC_KEY_PATH", "RAGFLOW_RSA_PUBLIC_KEY_PATH"):
            key_path = os.environ.get(env_name, "").strip()
            if key_path and Path(key_path).exists():
                public_key_pem = Path(key_path).read_text()
                break
    if not public_key_pem:
        default_public_key_path = Path(__file__).resolve().parents[2] / "conf" / "public.pem"
        if default_public_key_path.exists():
            public_key_pem = default_public_key_path.read_text()

    if not public_key_pem:
        return password_base64

    try:
        from Cryptodome.PublicKey import RSA
        from Cryptodome.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
        rsa_key = RSA.importKey(public_key_pem)
        cipher = Cipher_pkcs1_v1_5.new(rsa_key)
        encrypted_password = cipher.encrypt(password_base64.encode())
        return base64.b64encode(encrypted_password).decode('utf-8')
    except Exception as exc:
        raise AuthException("Password RSA encryption unavailable.") from exc


def register_user(client: HttpClient, email: str, nickname: str, password: str) -> None:
    password_enc = encrypt_password(password)
    payload = {"email": email, "nickname": nickname, "password": password_enc}
    res = client.request_json("POST", "/user/register", use_api_base=False, auth_kind=None, json_body=payload)
    if res.get("code") == 0:
        return
    msg = res.get("message", "")
    if "has already registered" in msg:
        return
    raise AuthException(f"Register failed: {msg}")


def login_user(client: HttpClient, server_type: str, email: str, password: str) -> str:
    password_enc = encrypt_password(password)
    payload = {"email": email, "password": password_enc}
    if server_type == "admin":
        response = client.request("POST", "/admin/login", use_api_base=True, auth_kind=None, json_body=payload)
    else:
        response = client.request("POST", "/user/login", use_api_base=False, auth_kind=None, json_body=payload)
    try:
        res = response.json()
    except Exception as exc:
        raise AuthException(f"Login failed: invalid JSON response ({exc})") from exc
    if res.get("code") != 0:
        raise AuthException(f"Login failed: {res.get('message')}")
    token = response.headers.get("Authorization")
    if not token:
        raise AuthException("Login failed: missing Authorization header")
    return token
