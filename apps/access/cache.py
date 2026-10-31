"""Кеш обчислених прав користувача між запитами (Redis у dev/prod).

Інвалідація — через версії, а не видалення ключів: ключ містить глобальну
версію (зміни ролей і каталогу дозволів) і версію користувача (видача /
відкликання його ролей). Після зміни версія зростає, тож навіть запит,
який паралельно встиг порахувати старі права, запише їх під ключ, який
більше ніхто не прочитає.

Кеш — лише оптимізація: якщо Redis недоступний, права рахуються з БД.
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

GLOBAL_VERSION_KEY = "access:version"


def _user_version_key(user_id):
    return f"access:version:user:{user_id}"


def _warn(action):
    logger.warning(
        "Access cache unavailable (%s), falling back to DB", action, exc_info=True
    )


def key_for(user_id):
    """Актуальний ключ для прав користувача або None, якщо кеш недоступний."""
    user_version_key = _user_version_key(user_id)
    try:
        versions = cache.get_many([GLOBAL_VERSION_KEY, user_version_key])
    except Exception:
        _warn("get versions")
        return None
    return (
        f"access:perms:{versions.get(GLOBAL_VERSION_KEY, 0)}:"
        f"{versions.get(user_version_key, 0)}:{user_id}"
    )


def load(key):
    if key is None:
        return None
    try:
        return cache.get(key)
    except Exception:
        _warn("get")
        return None


def store(key, value, timeout):
    if key is None or timeout <= 0:
        return
    try:
        cache.set(key, value, timeout)
    except Exception:
        _warn("set")


def _bump(version_key):
    try:
        cache.incr(version_key)
    except ValueError:  # ключа ще немає
        cache.set(version_key, 1, None)


def invalidate_user(user_id):
    try:
        _bump(_user_version_key(user_id))
    except Exception:
        _warn("invalidate user")


def invalidate_all():
    try:
        _bump(GLOBAL_VERSION_KEY)
    except Exception:
        _warn("invalidate all")
