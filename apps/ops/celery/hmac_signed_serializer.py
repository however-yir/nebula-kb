import hmac
import hashlib
import pickle
import os
import logging
from importlib import import_module
from kombu.serialization import register

logger = logging.getLogger('nebula.celery')

_local_secret_key = (
    os.environ.get('NEBULA_HMAC_SIGNED_SERIALIZER_SECRET_KEY')
    or os.environ.get('LZKB_HMAC_SIGNED_SERIALIZER_SECRET_KEY')
    or os.environ.get('MAXKB_HMAC_SIGNED_SERIALIZER_SECRET_KEY')
)
try:
    _local_secret_key = getattr(import_module('xpack'), 'get_' + 'm' + 'd5')()
except ImportError:
    pass

if not _local_secret_key:
    # 不再使用基于主机名/版本的可预测默认密钥: 优先复用部署 SECRET_KEY(生产环境强制配置)
    from django.core.exceptions import ImproperlyConfigured

    from lzkb.const import CONFIG

    _local_secret_key = CONFIG.get('SECRET_KEY')
    if not _local_secret_key:
        if CONFIG.get_environment() == 'prod':
            raise ImproperlyConfigured(
                'NEBULA_HMAC_SIGNED_SERIALIZER_SECRET_KEY (or SECRET_KEY) must be set in production environment')
        _local_secret_key = 'django-insecure-hmac-signed-serializer-dev-key'
        logger.warning('HMAC serializer secret key not configured, using insecure development default. '
                       'Set NEBULA_HMAC_SIGNED_SERIALIZER_SECRET_KEY or SECRET_KEY in production.')

def secure_dumps(obj):
    data = pickle.dumps(obj)
    signature = hmac.new(_local_secret_key.encode(), data, hashlib.sha256).digest()
    return signature + data

def secure_loads(signed_data):
    if len(signed_data) < 32:
        raise ValueError("Invalid signed data packet")
    signature = signed_data[:32]
    payload = signed_data[32:]
    expected_signature = hmac.new(_local_secret_key.encode(), payload, hashlib.sha256).digest()
    if hmac.compare_digest(signature, expected_signature):
        return pickle.loads(payload)
    else:
        raise ValueError("Security Alert: Task signature mismatch! Potential tampering detected.")

def register_hmac_signed_serializer():
    register(
        'hmac_signed_serializer',
        secure_dumps,
        secure_loads,
        content_type='application/x-python-hmac-signed-serialize',
        content_encoding='binary'
    )
