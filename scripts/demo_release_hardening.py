#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from system_manage.services.release_hardening_completion import ReleaseHardeningCompletion  # noqa: E402


def main() -> None:
    platform = ReleaseHardeningCompletion()
    summary = platform.summary()

    print("NebulaKB demo: release hardening completion")
    print(f"Service test matrix: {json.dumps(summary['service_tests'], sort_keys=True)}")
    print(f"Performance baselines: {json.dumps(summary['performance'], sort_keys=True)}")
    print(f"Docker Compose production: {summary['deployment']['docker_compose_production']}")
    print(f"Helm parameters: {summary['deployment']['helm_parameters']}")
    print(f"PgBouncer docs: {summary['deployment']['pgbouncer']}")
    print(f"Database backup/restore: {summary['deployment']['database_backup']} / {summary['deployment']['database_restore']}")
    print(f"Redis persistence: {summary['deployment']['redis_persistence']}")
    print(f"Static assets: {summary['deployment']['static_assets']}")
    print(f"Upgrade steps: {summary['deployment']['upgrade_steps']}")
    print(f"Prometheus metrics: {summary['observability']['prometheus_metrics']}")
    print(f"Grafana panels: {summary['observability']['grafana_panels']}")
    print(f"OpenTelemetry config: {summary['observability']['otel_config']}")
    print(f"Log fields: {summary['observability']['log_fields']}")
    print(f"Request id tracking: {summary['observability']['request_id']}")
    print(f"Slow query record: {summary['observability']['slow_query_record']}")
    print(f"Slow retrieval record: {summary['observability']['slow_retrieval_record']}")
    print(f"Celery task monitoring: {summary['observability']['celery_task_monitoring']}")


if __name__ == "__main__":
    main()
