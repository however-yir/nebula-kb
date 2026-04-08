from pathlib import Path

from django.test import SimpleTestCase


class ChatRouteSmokeTests(SimpleTestCase):
    def setUp(self):
        self.urls_content = Path(__file__).resolve().parent.joinpath("urls.py").read_text(encoding="utf-8")

    def test_routes_keep_core_chat_endpoints(self):
        self.assertIn("path('auth/anonymous', views.AnonymousAuthentication.as_view())", self.urls_content)
        self.assertIn("path('chat_message/<str:chat_id>', views.ChatView.as_view(), name='chat')", self.urls_content)

    def test_routes_keep_mcp_and_captcha_endpoints(self):
        self.assertIn("path('mcp', mcp_view)", self.urls_content)
        self.assertIn("path('captcha', views.CaptchaView.as_view(), name='captcha')", self.urls_content)
