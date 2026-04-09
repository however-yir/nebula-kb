from django.test import SimpleTestCase
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
