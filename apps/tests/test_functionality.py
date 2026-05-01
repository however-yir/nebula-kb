from unittest.mock import MagicMock

from django.test import SimpleTestCase


class KnowledgeVersionTests(SimpleTestCase):
    def test_version_serializer_importable(self):
        from knowledge.api.version import KnowledgeVersionSerializer
        self.assertIsNotNone(KnowledgeVersionSerializer)

    def test_version_serializer_fields(self):
        from knowledge.api.version import KnowledgeVersionSerializer
        serializer = KnowledgeVersionSerializer()
        self.assertIn('knowledge_id', serializer.fields)
        self.assertIn('version_number', serializer.fields)
        self.assertIn('name', serializer.fields)


class BatchAPITests(SimpleTestCase):
    def test_batch_import_serializer_importable(self):
        from knowledge.api.batch import BatchImportSerializer
        self.assertIsNotNone(BatchImportSerializer)

    def test_batch_export_serializer_importable(self):
        from knowledge.api.batch import BatchExportSerializer
        self.assertIsNotNone(BatchExportSerializer)

    def test_batch_export_format_choices(self):
        from knowledge.api.batch import BatchExportSerializer
        serializer = BatchExportSerializer()
        self.assertIn('format', serializer.fields)


class APIVersioningTests(SimpleTestCase):
    def test_api_v1_urls_in_patterns(self):
        from lzkb.urls.web import urlpatterns
        url_patterns_str = str(urlpatterns)
        self.assertIn('api/v1/', url_patterns_str)

    def test_admin_api_still_exists(self):
        from lzkb.settings.base.web import REST_FRAMEWORK
        self.assertIsNotNone(REST_FRAMEWORK)
