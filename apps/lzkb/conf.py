# coding=utf-8
"""
    @project: LZKB
    @Author：虎虎
    @file： conf.py
    @date：2025/4/11 16:58
    @desc:
"""
import errno
import logging
import os
from urllib.parse import unquote, urlparse

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
logger = logging.getLogger('lzkb.conf')


class Config(dict):
    defaults = {
        # 应用品牌与外链
        "APP_NAME": "NebulaKB",
        "APPSTORE_URL": "https://raw.githubusercontent.com/however-yir/LZKB/main/appstore/lzkb.json",
        "PROJECT_URL": "https://github.com/however-yir/LZKB",
        "HELP_URL": "https://github.com/however-yir/LZKB/wiki",
        "PRICING_URL": "https://github.com/however-yir/LZKB#readme",
        "CONTACT_URL": "https://github.com/however-yir/LZKB/issues",
        "OFFICIAL_SITE_URL": "https://github.com/however-yir/LZKB",
        "CHAT_FLOAT_ICON": "LZKB.gif",
        "ENVIRONMENT": "dev",
        "SECRET_KEY": "",
        "ALLOWED_HOSTS": "localhost,127.0.0.1",
        "CSRF_TRUSTED_ORIGINS": "",
        "CORS_ALLOWED_ORIGINS": "",
        "AUTH_ACCESS_TOKEN_TTL_SECONDS": 900,
        "AUTH_REFRESH_TOKEN_TTL_SECONDS": 604800,
        "TOKEN_EXPIRE": 900,
        "AUTH_COOKIE_SECURE": False,
        "AUTH_COOKIE_SAMESITE": "Lax",
        # 数据库相关配置
        "DATABASE_URL": "",
        "DB_NAME": "lzkb",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": 5432,
        "DB_USER": "root",
        "DB_PASSWORD": "CHANGE_ME_DB_PASSWORD",
        "DB_ENGINE": "dj_db_conn_pool.backends.postgresql",
        "DB_MAX_OVERFLOW": 80,
        'LOCAL_MODEL_HOST': '127.0.0.1',
        'LOCAL_MODEL_PORT': '11636',
        'LOCAL_MODEL_PROTOCOL': "http",
        'LOCAL_MODEL_HOST_WORKER': 1,
        'OLLAMA_BASE_URL': 'http://127.0.0.1:11434',
        'HTTP_LISTEN_PORT': 8080,
        'SCHEDULER_HTTP_PORT': 6060,
        # 语言
        'LANGUAGE_CODE': 'zh-CN',
        "DEBUG": False,
        # redis host
        "REDIS_URL": "",
        "REDIS_PROTOCOL": "redis",
        'REDIS_HOST': '127.0.0.1',
        # 端口
        'REDIS_PORT': 6379,
        # 密码
        'REDIS_PASSWORD': 'CHANGE_ME_REDIS_PASSWORD',
        # 库
        'REDIS_DB': 0,
        # 最大连接数
        'REDIS_MAX_CONNECTIONS': 100,
        # object storage
        "STORAGE_BACKEND": "local",
        "STORAGE_ENDPOINT": "",
        "STORAGE_BUCKET": "",
        "STORAGE_ACCESS_KEY": "",
        "STORAGE_SECRET_KEY": "",
        "STORAGE_REGION": "",
        "STORAGE_HEALTHCHECK_URL": "",
        "STORAGE_FORCE_PATH_STYLE": True,
        # health checks
        "MODEL_SERVICE_HEALTHCHECK_ENABLED": True,
        "MODEL_SERVICE_HEALTHCHECK_TIMEOUT": 3,
        "STORAGE_HEALTHCHECK_TIMEOUT": 3,
    }

    def get_debug(self) -> bool:
        value = self.get('DEBUG') if 'DEBUG' in self else True
        if isinstance(value, str):
            return value.lower() in {'1', 'true', 'yes', 'on'}
        return bool(value)

    def get_time_zone(self) -> str:
        return self.get('TIME_ZONE') if 'TIME_ZONE' in self else 'Asia/Shanghai'

    def get_db_setting(self) -> dict:
        return {
            "NAME": self.get('DB_NAME'),
            "HOST": self.get('DB_HOST'),
            "PORT": self.get('DB_PORT'),
            "USER": self.get('DB_USER'),
            "PASSWORD": self.get('DB_PASSWORD'),
            "ENGINE": self.get('DB_ENGINE'),
            "CONN_MAX_AGE": 0,
            "POOL_OPTIONS": {
                "POOL_SIZE": 20,
                "MAX_OVERFLOW": int(self.get('DB_MAX_OVERFLOW')),
                "RECYCLE": 1800,
                "PRE_PING": True,
                "TIMEOUT": 30
            }
        }

    def get_cache_setting(self):
        redis_config = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': (
                    f'{self.get("REDIS_PROTOCOL", "redis")}://'
                    f'{self.get("REDIS_HOST")}:{self.get("REDIS_PORT")}/{self.get("REDIS_DB")}'
                ),
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    "CONNECTION_POOL_KWARGS": {"max_connections": int(self.get("REDIS_MAX_CONNECTIONS"))}
                },
            },
        }
        if self.get("REDIS_PASSWORD"):
            redis_config['default']['OPTIONS']["PASSWORD"] = self.get("REDIS_PASSWORD")
        if self.get('REDIS_SENTINEL_SENTINELS') is not None:
            sentinels_str = self.get('REDIS_SENTINEL_SENTINELS')
            sentinels = [
                (host.strip(), int(port))
                for hostport in sentinels_str.split(',')
                for host, port in [hostport.strip().split(':')]
            ]

            redis_config['default']['LOCATION'] = f'redis://{self.get("REDIS_SENTINEL_MASTER")}/{self.get("REDIS_DB")}'
            redis_config['default']['OPTIONS'].update({
                'CLIENT_CLASS': 'django_redis.client.SentinelClient',
                'SENTINELS': sentinels,
                'SENTINEL_MASTER': self.get('REDIS_SENTINEL_MASTER'),
                'PASSWORD': self.get("REDIS_PASSWORD"),
            })

        return redis_config

    def normalize(self):
        self._apply_file_values()
        self._apply_aliases()
        self._apply_database_url()
        self._apply_redis_url()
        return self

    def _apply_file_values(self):
        for key, value in list(self.items()):
            if not key.endswith('_FILE') or not value:
                continue
            target_key = key[:-5]
            try:
                with open(value, 'rt', encoding='utf8') as f:
                    self[target_key] = f.read().strip()
            except OSError as exc:
                raise ImportError(f'Unable to load secret file for {target_key}: {value}') from exc

    def _apply_aliases(self):
        if self.get('ENV') and not self.get('ENVIRONMENT'):
            self['ENVIRONMENT'] = self.get('ENV')
        if self.get('TOKEN_EXPIRE') and not self.get('AUTH_ACCESS_TOKEN_TTL_SECONDS'):
            self['AUTH_ACCESS_TOKEN_TTL_SECONDS'] = self.get('TOKEN_EXPIRE')

    def _apply_database_url(self):
        database_url = self.get('DATABASE_URL')
        if not database_url:
            return
        parsed = urlparse(database_url)
        scheme = parsed.scheme.split('+', 1)[0]
        if scheme in ('postgres', 'postgresql'):
            self['DB_ENGINE'] = self.get('DB_ENGINE') or 'dj_db_conn_pool.backends.postgresql'
            if parsed.path and parsed.path != '/':
                self['DB_NAME'] = unquote(parsed.path.lstrip('/'))
            if parsed.hostname:
                self['DB_HOST'] = parsed.hostname
            if parsed.port:
                self['DB_PORT'] = parsed.port
            if parsed.username:
                self['DB_USER'] = unquote(parsed.username)
            if parsed.password:
                self['DB_PASSWORD'] = unquote(parsed.password)
        elif scheme in ('sqlite', 'sqlite3'):
            self['DB_ENGINE'] = 'django.db.backends.sqlite3'
            sqlite_name = unquote(parsed.path or parsed.netloc or ':memory:')
            if sqlite_name == '/:memory:':
                sqlite_name = ':memory:'
            elif sqlite_name.startswith('//'):
                sqlite_name = sqlite_name[1:]
            self['DB_NAME'] = sqlite_name

    def _apply_redis_url(self):
        redis_url = self.get('REDIS_URL')
        if not redis_url:
            return
        parsed = urlparse(redis_url)
        if parsed.scheme not in ('redis', 'rediss'):
            return
        self['REDIS_PROTOCOL'] = parsed.scheme
        if parsed.hostname:
            self['REDIS_HOST'] = parsed.hostname
        if parsed.port:
            self['REDIS_PORT'] = parsed.port
        self['REDIS_PASSWORD'] = unquote(parsed.password) if parsed.password is not None else ''
        if parsed.path and parsed.path != '/':
            redis_db = parsed.path.lstrip('/')
            self['REDIS_DB'] = int(redis_db) if redis_db.isdigit() else redis_db

    def get_language_code(self):
        return self.get('LANGUAGE_CODE', 'zh-CN')

    def get_environment(self):
        return self.get('ENVIRONMENT', 'dev')

    def get_storage_setting(self):
        return {
            'BACKEND': self.get('STORAGE_BACKEND', 'local'),
            'ENDPOINT': self.get('STORAGE_ENDPOINT', ''),
            'BUCKET': self.get('STORAGE_BUCKET', ''),
            'ACCESS_KEY': self.get('STORAGE_ACCESS_KEY', ''),
            'SECRET_KEY': self.get('STORAGE_SECRET_KEY', ''),
            'REGION': self.get('STORAGE_REGION', ''),
            'HEALTHCHECK_URL': self.get('STORAGE_HEALTHCHECK_URL', ''),
            'FORCE_PATH_STYLE': self.get('STORAGE_FORCE_PATH_STYLE', True),
        }

    def get_log_level(self):
        return self.get('LOG_LEVEL', 'DEBUG')

    def get_app_name(self):
        return self.get('APP_NAME', 'NebulaKB')

    def get_appstore_url(self):
        return self.get('APPSTORE_URL', self.defaults['APPSTORE_URL'])

    def get_project_url(self):
        return self.get('PROJECT_URL', self.defaults['PROJECT_URL'])

    def get_help_url(self):
        return self.get('HELP_URL', self.defaults['HELP_URL'])

    def get_pricing_url(self):
        return self.get('PRICING_URL', self.defaults['PRICING_URL'])

    def get_contact_url(self):
        return self.get('CONTACT_URL', self.defaults['CONTACT_URL'])

    def get_official_site_url(self):
        return self.get('OFFICIAL_SITE_URL', self.defaults['OFFICIAL_SITE_URL'])

    def get_chat_float_icon(self):
        return self.get('CHAT_FLOAT_ICON', self.defaults['CHAT_FLOAT_ICON'])

    def get_sandbox_python_package_paths(self):
        return self.get('SANDBOX_PYTHON_PACKAGE_PATHS',
                        '/opt/py3/lib/python3.11/site-packages,/opt/maxkb-app/sandbox/python-packages,/opt/maxkb/python-packages')

    def get_admin_path(self):
        return self.get('ADMIN_PATH', '/admin')

    def get_chat_path(self):
        return self.get('CHAT_PATH', '/chat')

    def get_session_timeout(self):
        return int(self.get('SESSION_TIMEOUT', 28800))

    def __init__(self, *args):
        super().__init__(*args)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))

    def __getitem__(self, item):
        return self.get(item)

    def __getattr__(self, item):
        return self.get(item)


class ConfigManager:
    config_class = Config

    def __init__(self, root_path=None):
        self.root_path = root_path
        self.config = self.config_class()
        for key in self.config_class.defaults:
            self.config[key] = self.config_class.defaults[key]

    def from_mapping(self, *mapping, **kwargs):
        """Updates the config like :meth:`update` ignoring items with non-upper
        keys.

        .. versionadded:: 0.11
        """
        mappings = []
        if len(mapping) == 1:
            if hasattr(mapping[0], 'items'):
                mappings.append(mapping[0].items())
            else:
                mappings.append(mapping[0])
        elif len(mapping) > 1:
            raise TypeError(
                'expected at most 1 positional argument, got %d' % len(mapping)
            )
        mappings.append(kwargs.items())
        for mapping in mappings:
            for (key, value) in mapping:
                if key.isupper():
                    self.config[key] = value
        return True

    def from_yaml(self, filename, silent=False):
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        try:
            with open(filename, 'rt', encoding='utf8') as f:
                obj = yaml.safe_load(f)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        if obj:
            return self.from_mapping(obj)
        return True

    def load_from_yml(self):
        env = os.environ.get('LZKB_ENVIRONMENT', os.environ.get('LZKB_ENV', os.environ.get('APP_ENV', '')))
        candidates = []
        if env:
            candidates.extend([
                f'config.{env}.yml',
                f'config.{env}.yaml',
                os.path.join('config', f'{env}.yml'),
                os.path.join('config', f'{env}.yaml'),
            ])
        candidates.extend(['config.yaml', 'config.yml', 'config_example.yml'])
        for i in candidates:
            if not os.path.isfile(os.path.join(self.root_path, i)):
                continue
            loaded = self.from_yaml(i)
            if loaded:
                return True
        msg = f"""

                   Error: No config file found.

                   You can run `cp config_example.yml {self.root_path}/config.yml`, and edit it.

                   """
        raise ImportError(msg)

    def load_from_env(self):
        keys = os.environ.keys()
        config = {}
        direct_env_keys = {
            'APP_ENV',
            'ENVIRONMENT',
            'DATABASE_URL',
            'DATABASE_URL_FILE',
            'REDIS_URL',
            'REDIS_URL_FILE',
            'REDIS_PROTOCOL',
            'SECRET_KEY',
            'SECRET_KEY_FILE',
            'TOKEN_EXPIRE',
            'STORAGE_BACKEND',
            'STORAGE_ENDPOINT',
            'STORAGE_BUCKET',
            'STORAGE_ACCESS_KEY',
            'STORAGE_ACCESS_KEY_FILE',
            'STORAGE_SECRET_KEY',
            'STORAGE_SECRET_KEY_FILE',
            'STORAGE_REGION',
            'STORAGE_HEALTHCHECK_URL',
            'STORAGE_FORCE_PATH_STYLE',
            'MODEL_SERVICE_HEALTHCHECK_ENABLED',
            'MODEL_SERVICE_HEALTHCHECK_TIMEOUT',
            'STORAGE_HEALTHCHECK_TIMEOUT',
        }
        for key in keys:
            if key.startswith('LZKB_'):
                config[key.replace('LZKB_', '')] = os.environ.get(key)
            elif key.startswith('MAXKB_') and key.replace('MAXKB_', '') not in config:
                # Backward compatibility for existing MAXKB deployments.
                config[key.replace('MAXKB_', '')] = os.environ.get(key)
            elif key in direct_env_keys and key not in config:
                config[key] = os.environ.get(key)
        if config.get('APP_ENV') and not config.get('ENVIRONMENT'):
            config['ENVIRONMENT'] = config.get('APP_ENV')
        if len(config.keys()) <= 0:
            msg = f"""

                             Error: No config env found.

                             Please set environment variables
                                LZKB_CONFIG_TYPE: 配置文件读取方式 FILE: 使用配置文件配置  ENV: 使用ENV配置
                                LZKB_DB_NAME: 数据库名称
                                LZKB_DB_HOST: 数据库主机
                                LZKB_DB_PORT: 数据库端口
                                LZKB_DB_USER: 数据库用户名
                                LZKB_DB_PASSWORD: 数据库密码
                                
                                LZKB_REDIS_HOST:缓存数据库主机
                                LZKB_REDIS_PORT:缓存数据库端口
                                LZKB_REDIS_PASSWORD:缓存数据库密码
                                LZKB_REDIS_DB:缓存数据库
                                LZKB_REDIS_MAX_CONNECTIONS:缓存数据库最大连接数
                             """
            raise ImportError(msg)
        self.from_mapping(config)
        return True

    @classmethod
    def load_user_config(cls, root_path=None, config_class=None):
        config_class = config_class or Config
        cls.config_class = config_class
        if not root_path:
            root_path = PROJECT_DIR
        manager = cls(root_path=root_path)
        config_type = os.environ.get('LZKB_CONFIG_TYPE', os.environ.get('MAXKB_CONFIG_TYPE'))
        env_contract_keys = (
            'DATABASE_URL',
            'DATABASE_URL_FILE',
            'REDIS_URL',
            'REDIS_URL_FILE',
            'SECRET_KEY',
            'SECRET_KEY_FILE',
        )
        if config_type is None and any(os.environ.get(key) for key in env_contract_keys):
            config_type = 'ENV'
        if config_type is None or config_type != 'ENV':
            manager.load_from_yml()
        else:
            manager.load_from_env()
        config = manager.config
        config.normalize()
        return config
