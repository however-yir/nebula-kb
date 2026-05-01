import logging
import os
import subprocess

from celery import shared_task

logger = logging.getLogger('nebula.backup')


@shared_task(bind=True, name='ops.postgres_backup')
def run_postgres_backup(self):
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'scripts', 'backup-postgres.sh')
    if not os.path.isfile(script):
        logger.error("Backup script not found: %s", script)
        return {'status': 'error', 'message': 'Backup script not found'}
    try:
        result = subprocess.run(['bash', script], capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            logger.info("Backup completed: %s", result.stdout.strip())
            return {'status': 'success', 'output': result.stdout.strip()}
        else:
            logger.error("Backup failed: %s", result.stderr.strip())
            return {'status': 'error', 'message': result.stderr.strip()}
    except subprocess.TimeoutExpired:
        logger.error("Backup timed out")
        return {'status': 'error', 'message': 'Backup timed out'}
