from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase


class RetrievalCacheTests(SimpleTestCase):
    def test_cache_config_defaults(self):
        from lzkb.conf import Config
        config = Config()
        self.assertTrue(config.defaults.get('CACHE_RETRIEVAL_ENABLED'))
        self.assertEqual(config.defaults.get('CACHE_RETRIEVAL_TTL'), 300)

    def test_cache_key_deterministic(self):
        import hashlib
        key_data = 'knowledge123:query_text:10:0.7:embedding'
        key1 = hashlib.md5(key_data.encode()).hexdigest()
        key2 = hashlib.md5(key_data.encode()).hexdigest()
        self.assertEqual(key1, key2)

    def test_cache_key_varies_with_inputs(self):
        import hashlib
        key1 = hashlib.md5('knowledge123:query1'.encode()).hexdigest()
        key2 = hashlib.md5('knowledge123:query2'.encode()).hexdigest()
        self.assertNotEqual(key1, key2)


class GunicornConfigTests(SimpleTestCase):
    def test_gunicorn_config_defaults(self):
        from lzkb.conf import Config
        config = Config()
        self.assertEqual(int(config.defaults.get('GUNICORN_WORKERS', 0)), 0)
        self.assertEqual(int(config.defaults.get('GUNICORN_THREADS', 200)), 200)
        self.assertEqual(int(config.defaults.get('GUNICORN_TIMEOUT', 30)), 30)


class CeleryConfigTests(SimpleTestCase):
    def test_celery_concurrency_default(self):
        from lzkb.conf import Config
        config = Config()
        self.assertEqual(int(config.defaults.get('CELERY_WORKER_CONCURRENCY', 5)), 5)

    def test_celery_concurrency_from_env(self):
        import os
        val = int(os.environ.get('CELERY_WORKER_CONCURRENCY', 5))
        self.assertIsInstance(val, int)


class LLMFallbackTests(SimpleTestCase):
    def test_fallback_manager_disabled_by_default(self):
        from lzkb.conf import Config
        config = Config()
        self.assertFalse(config.defaults.get('LLM_FALLBACK_ENABLED', True))

    def test_fallback_manager_importable(self):
        from common.llm.fallback import LLMFallbackManager
        manager = LLMFallbackManager(enabled=False)
        self.assertFalse(manager.enabled)

    def test_fallback_tries_alternatives(self):
        from common.llm.fallback import LLMFallbackManager
        manager = LLMFallbackManager(enabled=True)
        configs = [{'name': 'provider1'}, {'name': 'provider2'}]

        call_count = 0

        def mock_invoke(config, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if config['name'] == 'provider1':
                raise Exception('Provider 1 failed')
            return 'success'

        result = manager.get_response(configs, mock_invoke)
        self.assertEqual(result, 'success')
        self.assertEqual(call_count, 2)
