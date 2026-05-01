from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase, override_settings

from common.auth.throttle import AnonRateThrottleCustom, UserRateThrottleCustom, KnowledgeSearchThrottle
from common.middleware.audit import redact_dict, redact_body, AuditLogMiddleware, SENSITIVE_FIELDS
from common.middleware.security_headers import SecurityHeadersMiddleware


class SecretKeyGuardTests(SimpleTestCase):
    def test_default_insecure_key_identifiable(self):
        from lzkb.settings.base.web import _DEFAULT_INSECURE_KEY
        self.assertTrue(_DEFAULT_INSECURE_KEY.startswith('django-insecure-'))

    def test_secret_key_from_config(self):
        from lzkb.conf import Config
        config = Config()
        config['SECRET_KEY'] = 'test-secret-key'
        self.assertEqual(config.get('SECRET_KEY'), 'test-secret-key')


class ThrottleTests(SimpleTestCase):
    def test_anon_throttle_exists(self):
        self.assertEqual(AnonRateThrottleCustom.scope, 'anon')

    def test_user_throttle_exists(self):
        self.assertEqual(UserRateThrottleCustom.scope, 'user')

    def test_knowledge_search_throttle_exists(self):
        self.assertEqual(KnowledgeSearchThrottle.scope, 'knowledge_search')


class SSOProviderTests(SimpleTestCase):
    def test_sso_provider_model_importable(self):
        from users.models.sso_provider import SSOProvider
        self.assertTrue(hasattr(SSOProvider, 'PROVIDER_TYPES'))
        self.assertEqual(len(SSOProvider.PROVIDER_TYPES), 2)

    def test_sso_provider_fields(self):
        from users.models.sso_provider import SSOProvider
        field_names = [f.name for f in SSOProvider._meta.get_fields()]
        for expected in ['name', 'provider_type', 'client_id', 'client_secret', 'discovery_url', 'redirect_uri', 'is_active']:
            self.assertIn(expected, field_names)


class AuditRedactionTests(SimpleTestCase):
    def test_redact_dict_password(self):
        data = {'username': 'admin', 'password': 'secret123'}
        result = redact_dict(data)
        self.assertEqual(result['username'], 'admin')
        self.assertEqual(result['password'], '***REDACTED***')

    def test_redact_dict_nested(self):
        data = {'user': {'name': 'test', 'token': 'abc123'}}
        result = redact_dict(data)
        self.assertEqual(result['user']['name'], 'test')
        self.assertEqual(result['user']['token'], '***REDACTED***')

    def test_redact_body_json(self):
        body = '{"username": "admin", "password": "secret"}'
        result = redact_body(body)
        self.assertIn('***REDACTED***', result)
        self.assertIn('admin', result)

    def test_redact_body_plain_text(self):
        body = 'not json'
        result = redact_body(body)
        self.assertEqual(result, 'not json')

    def test_sensitive_fields_set(self):
        self.assertIn('password', SENSITIVE_FIELDS)
        self.assertIn('token', SENSITIVE_FIELDS)
        self.assertIn('secret', SENSITIVE_FIELDS)
        self.assertIn('api_key', SENSITIVE_FIELDS)


class SecurityHeadersTests(SimpleTestCase):
    def test_security_headers_middleware_exists(self):
        middleware = SecurityHeadersMiddleware(lambda r: None)
        self.assertIsNotNone(middleware)

    def test_security_headers_added(self):
        from django.http import HttpResponse
        middleware = SecurityHeadersMiddleware(lambda r: HttpResponse())
        request = MagicMock()
        response = middleware.process_response(request, HttpResponse())
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertIn('Referrer-Policy', response)
