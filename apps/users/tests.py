from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from common.exception.app_exception import AppApiException
from tests.factories import make_mock_user
from users.serializers.login import LoginSerializer


TOKEN_PAYLOAD = {
    "access_token": "access-token",
    "refresh_token": "refresh-token",
    "token_type": "Bearer",
    "expires_in": 900,
    "refresh_expires_in": 604800,
    "user_id": "a8e2dc0d-8d09-4e95-a570-8e6bb44a49d2",
    "session_id": "session-id",
    "device_id": "device-id",
}


class LoginSerializerTests(SimpleTestCase):
    def test_login_success_returns_access_refresh_tokens(self):
        fake_user = make_mock_user()
        user_query = MagicMock()
        user_query.first.return_value = fake_user

        with (
            patch.object(
                LoginSerializer,
                "get_auth_setting",
                return_value={"max_attempts": -1, "failed_attempts": 5, "lock_time": 10},
            ),
            patch(
                "users.serializers.login.DatabaseModelManage.get_model",
                return_value=lambda: False,
            ),
            patch("users.serializers.login.User.objects.filter", return_value=user_query),
            patch("users.serializers.login.password_matches", return_value=True) as mock_password_matches,
            patch("users.serializers.login.cache.delete") as mock_cache_delete,
            patch("users.serializers.login.create_device_session", return_value=TOKEN_PAYLOAD) as mock_create_session,
        ):
            result = LoginSerializer.login({"username": "demo-user", "password": "pass@123"})

        self.assertEqual(result, TOKEN_PAYLOAD)
        mock_password_matches.assert_called_once_with("pass@123", fake_user.password)
        mock_create_session.assert_called_once()
        self.assertGreaterEqual(mock_cache_delete.call_count, 2)

    def test_login_raises_error_when_credentials_invalid(self):
        user_query = MagicMock()
        user_query.first.return_value = None

        with (
            patch.object(
                LoginSerializer,
                "get_auth_setting",
                return_value={"max_attempts": -1, "failed_attempts": 5, "lock_time": 10},
            ),
            patch(
                "users.serializers.login.DatabaseModelManage.get_model",
                return_value=lambda: False,
            ),
            patch("users.serializers.login.User.objects.filter", return_value=user_query),
            patch("users.serializers.login.password_matches", return_value=False),
            patch.object(LoginSerializer, "_handle_failed_login") as mock_handle_failed,
        ):
            with self.assertRaises(AppApiException) as ctx:
                LoginSerializer.login({"username": "demo-user", "password": "wrong-password"})

        self.assertEqual(ctx.exception.code, 500)
        self.assertEqual(ctx.exception.message, "The username or password is incorrect")
        mock_handle_failed.assert_called_once_with("demo-user", False, 5, 10)

    def test_need_captcha_when_reaching_max_attempts(self):
        with patch("users.serializers.login.cache.get", return_value=3):
            self.assertTrue(LoginSerializer._need_captcha("demo-user", 3))

    def test_is_account_locked_detects_existing_lock_cache(self):
        with patch("users.serializers.login.cache.get", return_value=1):
            self.assertTrue(LoginSerializer._is_account_locked("demo-user", 5))

    def test_handle_failed_login_returns_remaining_attempts_message(self):
        with (
            patch("users.serializers.login.record_login_fail"),
            patch("users.serializers.login.record_login_fail_lock", return_value=3),
            patch("users.serializers.login.cache.add"),
        ):
            with self.assertRaises(AppApiException) as ctx:
                LoginSerializer._handle_failed_login(
                    username="demo-user",
                    is_license_valid=True,
                    failed_attempts=5,
                    lock_time=10,
                )

        self.assertEqual(ctx.exception.code, 1005)
        self.assertIn("you have 2 more chances", str(ctx.exception.message))

    def test_handle_failed_login_locks_account_after_threshold(self):
        with (
            patch("users.serializers.login.record_login_fail"),
            patch("users.serializers.login.record_login_fail_lock", return_value=5),
            patch("users.serializers.login.cache.add") as mock_add_lock,
        ):
            with self.assertRaises(AppApiException) as ctx:
                LoginSerializer._handle_failed_login(
                    username="demo-user",
                    is_license_valid=True,
                    failed_attempts=5,
                    lock_time=10,
                )

        mock_add_lock.assert_called_once()
        self.assertEqual(ctx.exception.code, 1005)
        self.assertIn("This account has been locked for 10 minutes", str(ctx.exception.message))
