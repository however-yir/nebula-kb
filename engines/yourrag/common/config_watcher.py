"""
Config hot-reload: watches service_conf.yaml for changes and triggers reload.
No restart needed for config updates.
"""
import os
import logging
import threading
import time

logger = logging.getLogger(__name__)

_watch_enabled = os.environ.get("CONFIG_HOT_RELOAD", "0") == "1"
_watcher_thread = None
_last_mtime = 0


def _get_config_path():
    from common.file_utils import get_project_base_directory
    from common.constants import SERVICE_CONF
    return os.path.join(get_project_base_directory(), "conf", SERVICE_CONF)


def _watch_loop(callback, interval=5):
    global _last_mtime
    config_path = _get_config_path()
    try:
        _last_mtime = os.path.getmtime(config_path)
    except OSError:
        _last_mtime = 0

    while True:
        time.sleep(interval)
        try:
            current_mtime = os.path.getmtime(config_path)
            if current_mtime != _last_mtime:
                _last_mtime = current_mtime
                logger.info(f"Config file changed: {config_path}, reloading...")
                try:
                    callback()
                    logger.info("Config reloaded successfully")
                except Exception as e:
                    logger.error(f"Config reload failed: {e}")
        except OSError:
            pass


def start_config_watcher(callback, interval=5):
    """Start watching config file for changes. Calls callback() on change."""
    global _watcher_thread
    if not _watch_enabled:
        return
    if _watcher_thread and _watcher_thread.is_alive():
        return
    _watcher_thread = threading.Thread(
        target=_watch_loop, args=(callback, interval), daemon=True, name="config-watcher"
    )
    _watcher_thread.start()
    logger.info(f"Config hot-reload enabled (interval={interval}s)")
