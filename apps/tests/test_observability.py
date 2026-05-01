import json
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from common.middleware.tracing import OTelTracingMiddleware


class PrometheusTests(SimpleTestCase):
    def test_prometheus_in_installed_apps(self):
        from lzkb.settings.base.web import INSTALLED_APPS
        self.assertIn('django_prometheus', INSTALLED_APPS)

    def test_prometheus_middleware_installed(self):
        from lzkb.settings.base.web import MIDDLEWARE
        self.assertIn('django_prometheus.middleware.PrometheusBeforeMiddleware', MIDDLEWARE)
        self.assertIn('django_prometheus.middleware.PrometheusAfterMiddleware', MIDDLEWARE)


class OTelTracingTests(SimpleTestCase):
    def test_otel_middleware_creates_correlation_id(self):
        middleware = OTelTracingMiddleware(lambda r: MagicMock())
        request = MagicMock()
        request.META = {}
        request.method = 'GET'
        request.path = '/test'
        request.build_absolute_uri.return_value = 'http://localhost/test'
        middleware.process_request(request)
        self.assertTrue(hasattr(request, '_correlation_id'))
        self.assertTrue(len(request._correlation_id) > 0)

    def test_otel_middleware_sets_response_header(self):
        from django.http import HttpResponse
        middleware = OTelTracingMiddleware(lambda r: HttpResponse())
        request = MagicMock()
        request.META = {}
        request._correlation_id = 'test-correlation-id'
        response = middleware.process_response(request, HttpResponse())
        self.assertEqual(response['X-Request-ID'], 'test-correlation-id')

    def test_otel_handles_no_opentelemetry(self):
        from common.middleware import tracing
        self.assertIsNotNone(tracing)


class GrafanaDashboardTests(SimpleTestCase):
    def test_dashboard_json_valid(self):
        import os
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'deploy', 'grafana', 'dashboards', 'nebula-kb-overview.json'
        )
        with open(dashboard_path) as f:
            data = json.load(f)
        self.assertEqual(data['title'], 'NebulaKB Overview')
        self.assertTrue(len(data['panels']) > 0)
        self.assertIn('uid', data)

    def test_grafana_provisioning_exists(self):
        import os
        prov_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'deploy', 'grafana', 'provisioning', 'dashboards', 'nebula.yml'
        )
        self.assertTrue(os.path.exists(prov_path))


class FlowerComposeTests(SimpleTestCase):
    def test_flower_in_compose(self):
        import os
        import yaml
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'deploy', 'docker-compose.operational.yml'
        )
        with open(compose_path) as f:
            content = f.read()
        self.assertIn('flower', content)
        self.assertIn('--port=5555', content)
