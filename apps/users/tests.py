from unittest.mock import MagicMock, patch

from django.core import signing
from django.test import SimpleTestCase

from common.constants.authentication_type import AuthenticationType
from common.constants.cache_version import Cache_Version
from common.exception.app_exception import AppApiException
from tests.factories import make_mock_user
from users.serializers.login import LoginSerializer


class LoginSerializerTests(SimpleTestCase):
    def test_login_success_returns_signed_token_and_caches_user(self):
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
            patch("users.serializers.login.cache.delete") as mock_cache_delete,
            patch("users.serializers.login.cache.set") as mock_cache_set,
        ):
            result = LoginSerializer.login({"username": "demo-user", "password": "pass@123"})

        self.assertIn("token", result)
        token_payload = signing.loads(result["token"])
        self.assertEqual(token_payload["username"], fake_user.username)
        self.assertEqual(token_payload["email"], fake_user.email)
        self.assertEqual(token_payload["type"], AuthenticationType.SYSTEM_USER.value)

        _, get_key = Cache_Version.TOKEN.value
        self.assertEqual(mock_cache_set.call_count, 1)
        self.assertEqual(mock_cache_set.call_args.args[0], get_key(result["token"]))
        self.assertEqual(mock_cache_set.call_args.args[1], fake_user)
        self.assertIn("timeout", mock_cache_set.call_args.kwargs)
        self.assertIn("version", mock_cache_set.call_args.kwargs)
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
            LoginSerializer._handle_failed_login(
                username="demo-user",
                is_license_valid=True,
                failed_attempts=5,
                lock_time=10,
            )

        mock_add_lock.assert_called_once()
