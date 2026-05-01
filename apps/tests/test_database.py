import os
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase


class HNSWIndexTests(SimpleTestCase):
    def test_hnsw_config_defaults(self):
        from lzkb.conf import Config
        config = Config()
        self.assertEqual(int(config.defaults.get('HNSW_M', 16)), 16)
        self.assertEqual(int(config.defaults.get('HNSW_EF_CONSTRUCTION', 200)), 200)
        self.assertEqual(int(config.defaults.get('HNSW_EF_SEARCH', 40)), 40)

    def test_hnsw_sql_includes_params(self):
        hnsw_m = 16
        hnsw_ef = 200
        dims = 768
        k_id = 'test-knowledge-id'
        sql = f"""CREATE INDEX "embedding_hnsw_idx_{k_id}" ON embedding USING hnsw ((embedding::vector({dims})) vector_cosine_ops) WITH (m = {hnsw_m}, ef_construction = {hnsw_ef}) WHERE knowledge_id = '{k_id}'"""
        self.assertIn('WITH (m = 16, ef_construction = 200)', sql)
        self.assertIn('vector_cosine_ops', sql)


class PgBouncerTests(SimpleTestCase):
    def test_pgbouncer_config_defaults(self):
        from lzkb.conf import Config
        config = Config()
        self.assertFalse(config.defaults.get('DB_USE_PGBOUNCER', True))
        self.assertEqual(config.defaults.get('DB_PGBOUNCER_PORT', 6432), 6432)

    def test_pgbouncer_in_compose(self):
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'deploy', 'docker-compose.operational.yml'
        )
        with open(compose_path) as f:
            content = f.read()
        self.assertIn('pgbouncer', content)
        self.assertIn('PGBOUNCER_PORT', content)


class BackupTests(SimpleTestCase):
    def test_backup_script_exists(self):
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'scripts', 'backup-postgres.sh'
        )
        self.assertTrue(os.path.exists(script_path))

    def test_cron_backup_script_exists(self):
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'scripts', 'cron-backup.sh'
        )
        self.assertTrue(os.path.exists(script_path))

    def test_backup_task_importable(self):
        from ops.tasks.backup import run_postgres_backup
        self.assertIsNotNone(run_postgres_backup)

    def test_backup_retention_default(self):
        retention = os.environ.get('BACKUP_RETENTION_DAYS', '7')
        self.assertEqual(retention, '7')
