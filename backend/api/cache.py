"""Необязательный кэш дашборда в Redis. Если Redis выключен или недоступен, всё работает без него."""
import json
import logging

from common.config import settings

log = logging.getLogger("cache")
KEY = "dashboard:v1"
TTL = 30  # секунд
_client = None


def _redis():
    global _client
    if not settings.redis_enabled:
        return None
    if _client is None:
        import redis

        _client = redis.Redis.from_url(settings.redis_url, socket_timeout=1, socket_connect_timeout=1)
    return _client


def get_dashboard() -> dict | None:
    try:
        r = _redis()
        raw = r.get(KEY) if r else None
        return json.loads(raw) if raw else None
    except Exception as exc:
        log.warning("Redis недоступен: %s", exc)
        return None


def set_dashboard(data: dict) -> None:
    try:
        r = _redis()
        if r:
            r.setex(KEY, TTL, json.dumps(data))
    except Exception as exc:
        log.warning("Redis недоступен: %s", exc)


def invalidate() -> None:
    """Сбрасываем кэш после любого изменения данных."""
    try:
        r = _redis()
        if r:
            r.delete(KEY)
    except Exception as exc:
        log.warning("Redis недоступен: %s", exc)
