"""
LLM response caching layer to reduce redundant API calls.
Uses Redis for distributed caching with configurable TTL.
"""
import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)

_LLM_CACHE_ENABLED = os.environ.get("LLM_CACHE_ENABLED", "0") == "1"
_LLM_CACHE_TTL = int(os.environ.get("LLM_CACHE_TTL_SECONDS", "3600"))  # 1 hour default
_LLM_CACHE_PREFIX = "yourrag:llm_cache:"

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        try:
            from rag.utils.redis_conn import REDIS_CONN
            _redis = REDIS_CONN
        except Exception:
            logger.debug("LLM cache: Redis not available, caching disabled")
    return _redis


def _cache_key(model: str, messages: list, **kwargs) -> str:
    """Generate a deterministic cache key from request parameters."""
    payload = {
        "model": model,
        "messages": messages,
        "kwargs": {k: v for k, v in sorted(kwargs.items()) if k in ("temperature", "top_p", "max_tokens")},
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return _LLM_CACHE_PREFIX + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(model: str, messages: list, **kwargs):
    """Retrieve cached LLM response. Returns None if not cached."""
    if not _LLM_CACHE_ENABLED:
        return None
    redis = _get_redis()
    if not redis:
        return None
    try:
        key = _cache_key(model, messages, **kwargs)
        cached = redis.get(key)
        if cached:
            logger.debug(f"LLM cache hit: {model}")
            return json.loads(cached)
    except Exception as e:
        logger.debug(f"LLM cache get error: {e}")
    return None


def set_cached(model: str, messages: list, response: dict, **kwargs):
    """Cache an LLM response."""
    if not _LLM_CACHE_ENABLED:
        return
    redis = _get_redis()
    if not redis:
        return
    try:
        key = _cache_key(model, messages, **kwargs)
        redis.set(key, json.dumps(response, ensure_ascii=False), ex=_LLM_CACHE_TTL)
        logger.debug(f"LLM cache set: {model} (TTL={_LLM_CACHE_TTL}s)")
    except Exception as e:
        logger.debug(f"LLM cache set error: {e}")
