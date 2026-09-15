"""Optional Redis cache for slot queries."""
import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
_client = None
_failed = False


def get_redis():
    global _client, _failed
    settings = get_settings()
    if not settings.redis_enabled or _failed:
        return None
    if _client is None:
        try:
            import redis

            _client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
            _client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable, cache disabled: %s", exc)
            _failed = True
            _client = None
    return _client


def cache_get(key: str) -> Any | None:
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:  # noqa: BLE001
        pass


def cache_delete_pattern(pattern: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        for key in r.scan_iter(match=pattern, count=100):
            r.delete(key)
    except Exception:  # noqa: BLE001
        pass
