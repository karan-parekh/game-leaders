from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from typing import Any, Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)

_cache: Optional["aioredis.Redis"] = None


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379")


async def init_redis() -> Optional["aioredis.Redis"]:
    global _cache
    if aioredis is None:
        logger.warning("redis.asyncio not installed, leaderboard cache disabled")
        return None
    try:
        _cache = aioredis.from_url(get_redis_url(), decode_responses=True)
        await _cache.ping()
        logger.info("Redis connected at %s", get_redis_url())
        return _cache
    except Exception:
        logger.warning("Redis unavailable at %s, cache disabled", get_redis_url(), exc_info=True)
        _cache = None
        return None


async def close_redis() -> None:
    global _cache
    if _cache:
        await _cache.aclose()
        _cache = None


def redis_client() -> Optional["aioredis.Redis"]:
    return _cache


LEADERBOARD_TTL = 60
LOCK_TTL = 10
LEADERBOARD_KEY_PREFIX = "leaderboard:game:"
LEADERBOARD_VERSION_SUFFIX = ":version"
STORE_IF_VERSION_MATCHES = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
end
return 0
"""
INVALIDATE_IF_VERSIONED = """
redis.call('INCR', KEYS[1])
return redis.call('DEL', KEYS[2])
"""
RELEASE_LOCK_IF_OWNER = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


def etag(body: list[dict]) -> str:
    return '"' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32] + '"'


async def get_cached_leaderboard(game_id: str, build_fn, *args, **kwargs) -> tuple[list[dict], bool]:
    cache = redis_client()
    if cache is None:
        return await build_fn(*args, **kwargs), False

    key = f"{LEADERBOARD_KEY_PREFIX}{game_id}"
    version_key = f"{key}{LEADERBOARD_VERSION_SUFFIX}"

    try:
        cached = await cache.get(key)
        if cached is not None:
            return json.loads(cached), True
    except Exception:
        logger.warning("Redis GET failed, rebuilding from DB", exc_info=True)

    lock_key = f"{key}:lock"
    lock_token = uuid.uuid4().hex
    try:
        version = await cache.get(version_key)
        if version is None:
            version = str(await cache.incr(version_key))
    except Exception:
        logger.warning("Redis version check failed, rebuilding from DB", exc_info=True)
        version = None

    try:
        acquired = await cache.set(lock_key, lock_token, nx=True, ex=LOCK_TTL)
        if not acquired:
            await asyncio.sleep(0.1)
            return await get_cached_leaderboard(game_id, build_fn, *args, **kwargs)
    except Exception:
        pass

    try:
        rows = await build_fn(*args, **kwargs)
        if cache and version is not None:
            try:
                await cache.eval(
                    STORE_IF_VERSION_MATCHES,
                    2,
                    version_key,
                    key,
                    version,
                    json.dumps(rows),
                    LEADERBOARD_TTL,
                )
            except Exception:
                logger.warning("Redis SET failed", exc_info=True)
        return rows, False
    finally:
        if cache:
            try:
                await cache.eval(RELEASE_LOCK_IF_OWNER, 1, lock_key, lock_token)
            except Exception:
                pass


async def invalidate_leaderboard(game_id: str) -> None:
    cache = redis_client()
    if cache is None:
        return
    try:
        key = f"{LEADERBOARD_KEY_PREFIX}{game_id}"
        await cache.eval(INVALIDATE_IF_VERSIONED, 2, f"{key}{LEADERBOARD_VERSION_SUFFIX}", key)
    except Exception:
        logger.warning("Redis invalidation failed for game %s", game_id, exc_info=True)
