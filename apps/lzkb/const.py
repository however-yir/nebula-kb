# -*- coding: utf-8 -*-
#
import os

from dotenv import load_dotenv

from .conf import ConfigManager

__all__ = ['BASE_DIR', 'PROJECT_DIR', 'VERSION', 'CONFIG']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA_DIR = os.getenv('LZKB_DATA_DIR', os.getenv('MAXKB_DATA_DIR', os.path.join('/', 'opt', 'maxkb')))
LOG_DIR = os.path.join(APP_DATA_DIR, 'logs')
PROJECT_DIR = os.path.dirname(BASE_DIR)
VERSION = '2.0.0'

# load environment variables from .env file
load_dotenv()
# print(os.getenv('LZKB_CONFIG'))
if os.getenv('LZKB_CONFIG') is not None or os.getenv('MAXKB_CONFIG') is not None:
    CONFIG = ConfigManager.load_user_config(root_path=PROJECT_DIR)
else:
    conf_dir = os.getenv('LZKB_CONF_DIR', os.getenv('MAXKB_CONF_DIR', os.path.abspath('/opt/maxkb/conf')))
    CONFIG = ConfigManager.load_user_config(root_path=conf_dir)
