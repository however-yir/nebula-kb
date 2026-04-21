from unittest.mock import patch

from django.test import Client, SimpleTestCase
from django.urls import resolve

from lzkb.const import CONFIG


class ChatRouteSmokeTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.chat_api_prefix = f"{CONFIG.get_chat_path()}/api"

    def _resolve(self, path: str):
        return resolve(f"{self.chat_api_prefix}{path}")

    def test_routes_keep_core_chat_endpoints(self):
        anonymous_match = self._resolve("/auth/anonymous")
        chat_match = self._resolve("/chat_message/chat-1")

        self.assertEqual(anonymous_match.func.view_class.__name__, "AnonymousAuthentication")
        self.assertEqual(chat_match.view_name, "chat")
        self.assertEqual(chat_match.func.view_class.__name__, "ChatView")

    def test_routes_keep_mcp_and_captcha_endpoints(self):
        mcp_match = self._resolve("/mcp")
        captcha_match = self._resolve("/captcha")

        self.assertEqual(mcp_match.func.__name__, "mcp_view")
        self.assertEqual(captcha_match.view_name, "captcha")
        self.assertEqual(captcha_match.func.view_class.__name__, "CaptchaView")


class HealthRouteSmokeTests(SimpleTestCase):
    def test_healthz_is_lightweight(self):
        response = Client(HTTP_HOST="localhost").get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["checks"], {})

    def test_readyz_returns_dependency_payload(self):
        checks = {
            "database": lambda: {"status": "ok"},
            "cache": lambda: {"status": "ok"},
            "model_service": lambda: {"status": "skipped"},
            "object_storage": lambda: {"status": "skipped"},
        }

        with patch.dict("lzkb.health.READINESS_CHECKS", checks, clear=True):
            response = Client(HTTP_HOST="localhost").get("/readyz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["checks"]["database"]["status"], "ok")

    def test_readyz_fails_when_dependency_fails(self):
        checks = {
            "database": lambda: {"status": "ok"},
            "cache": lambda: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
        }

        with patch.dict("lzkb.health.READINESS_CHECKS", checks, clear=True):
            response = Client(HTTP_HOST="localhost").get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["checks"]["cache"]["status"], "error")
