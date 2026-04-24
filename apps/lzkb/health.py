import json
import os
from http import HTTPStatus
from urllib.request import Request, urlopen

from django.core.cache import caches
from django.db import connection
from django.http import JsonResponse

from lzkb.const import CONFIG, VERSION


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


def _timeout(config_key, default=3):
    try:
        return float(CONFIG.get(config_key, default))
    except (TypeError, ValueError):
        return default


def _check_database():
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.fetchone()
    return {'status': 'ok'}


def _check_cache():
    cache = caches['default']
    key = 'nebula:readyz'
    cache.set(key, 'ok', timeout=5)
    if cache.get(key) != 'ok':
        raise RuntimeError('cache write/read probe failed')
    return {'status': 'ok'}


def _check_model_service():
    if os.environ.get('SERVER_NAME') == 'local_model':
        return {'status': 'skipped', 'reason': 'current service is local_model'}
    if not _as_bool(CONFIG.get('MODEL_SERVICE_HEALTHCHECK_ENABLED', True)):
        return {'status': 'skipped', 'reason': 'disabled by config'}

    protocol = CONFIG.get('LOCAL_MODEL_PROTOCOL', 'http')
    host = CONFIG.get('LOCAL_MODEL_HOST', '127.0.0.1')
    port = CONFIG.get('LOCAL_MODEL_PORT', '11636')
    url = f'{protocol}://{host}:{port}/healthz'
    request = Request(url, method='GET')
    with urlopen(request, timeout=_timeout('MODEL_SERVICE_HEALTHCHECK_TIMEOUT')) as response:
        if response.status >= HTTPStatus.BAD_REQUEST:
            raise RuntimeError(f'model service returned HTTP {response.status}')
    return {'status': 'ok', 'url': url}


def _check_object_storage():
    storage = CONFIG.get_storage_setting()
    backend = storage.get('BACKEND', 'local')
    endpoint = storage.get('ENDPOINT')
    if backend == 'local' and not endpoint:
        return {'status': 'skipped', 'reason': 'local storage backend'}

    healthcheck_url = storage.get('HEALTHCHECK_URL')
    if healthcheck_url:
        request = Request(healthcheck_url, method='GET')
        with urlopen(request, timeout=_timeout('STORAGE_HEALTHCHECK_TIMEOUT')) as response:
            if response.status >= HTTPStatus.BAD_REQUEST:
                raise RuntimeError(f'object storage returned HTTP {response.status}')
        return {'status': 'ok', 'url': healthcheck_url}

    bucket = storage.get('BUCKET')
    if not endpoint or not bucket:
        raise RuntimeError('object storage endpoint and bucket must be configured')

    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=storage.get('ACCESS_KEY') or None,
        aws_secret_access_key=storage.get('SECRET_KEY') or None,
        region_name=storage.get('REGION') or None,
        config=BotoConfig(s3={'addressing_style': 'path' if _as_bool(storage.get('FORCE_PATH_STYLE')) else 'auto'}),
    )
    client.head_bucket(Bucket=bucket)
    return {'status': 'ok', 'endpoint': endpoint, 'bucket': bucket}


READINESS_CHECKS = {
    'database': _check_database,
    'cache': _check_cache,
    'model_service': _check_model_service,
    'object_storage': _check_object_storage,
}


def run_readiness_checks(include_dependencies=True):
    checks = {}
    if include_dependencies:
        for name, check in READINESS_CHECKS.items():
            try:
                checks[name] = check()
            except Exception as exc:
                checks[name] = {'status': 'error', 'error': str(exc)}

    ok = all(value.get('status') in {'ok', 'skipped'} for value in checks.values())
    return {
        'status': 'ok' if ok else 'error',
        'service': os.environ.get('SERVER_NAME', 'web'),
        'environment': CONFIG.get_environment(),
        'version': VERSION,
        'checks': checks,
    }, ok


def healthz(request):
    payload, _ = run_readiness_checks(include_dependencies=False)
    return JsonResponse(payload)


def readyz(request):
    payload, ok = run_readiness_checks(include_dependencies=True)
    return JsonResponse(payload, status=HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE)


def health_payload_json(include_dependencies=True):
    payload, ok = run_readiness_checks(include_dependencies=include_dependencies)
    return json.dumps(payload, ensure_ascii=False), ok
