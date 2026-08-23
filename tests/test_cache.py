import asyncio
import json

import pytest

import app.cache as cache_module
from app.db import SessionLocal


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.values[key] = value

    async def delete(self, key):
        self.values.pop(key, None)

    async def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = str(value)
        return value

    async def eval(self, script, numkeys, *args):
        if "redis.call('INCR'" in script:
            version_key, payload_key = args
            self.values[version_key] = str(int(self.values.get(version_key, 0)) + 1)
            self.values.pop(payload_key, None)
            return 1
        if "redis.call('DEL'" in script:
            lock_key, token = args
            if self.values.get(lock_key) == token:
                self.values.pop(lock_key, None)
                return 1
            return 0
        version_key, payload_key, token = args[:3]
        if self.values.get(version_key) != token:
            return 0
        if "redis.call('SET'" not in script:
            return self.values.get(payload_key)
        payload = args[3]
        self.values[payload_key] = payload
        return 1


class LockStealingRedis(FakeRedis):
    async def set(self, key, value, nx=False, ex=None):
        result = await super().set(key, value, nx=nx, ex=ex)
        self.values[key] = "new-owner"
        return result


@pytest.mark.asyncio
async def test_expired_lock_owner_cannot_delete_replacement_lock(monkeypatch):
    redis = LockStealingRedis()
    monkeypatch.setattr(cache_module, "_cache", redis)

    async def build():
        return [{"score": 1}]

    await cache_module.get_cached_leaderboard("game", build)

    assert redis.values["leaderboard:game:game:lock"] == "new-owner"


@pytest.mark.asyncio
async def test_invalidation_cannot_be_followed_by_stale_population(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(cache_module, "_cache", redis)
    started = asyncio.Event()
    release = asyncio.Event()

    async def build():
        started.set()
        await release.wait()
        return [{"score": 1}]

    read = asyncio.create_task(cache_module.get_cached_leaderboard("game", build))
    await started.wait()
    await cache_module.invalidate_leaderboard("game")
    release.set()
    assert await read == ([{"score": 1}], False)
    assert await redis.get("leaderboard:game:game") is None


@pytest.mark.asyncio
async def test_invalidation_bumps_version_and_deletes_payload_atomically(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(cache_module, "_cache", redis)
    key = "leaderboard:game:game"
    redis.values[key] = json.dumps([{"score": 1}])
    await cache_module.invalidate_leaderboard("game")

    assert redis.values[f"{key}:version"] == "1"
    assert key not in redis.values


@pytest.mark.asyncio
async def test_timeout_transition_invalidates_leaderboard_cache(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app import main
    from app.models import GameDefinition, GameSession, SessionState, User

    async with SessionLocal() as db:
        game = GameDefinition(name="Timeout Game", default_timeout_minutes=60, metrics=[])
        user = User(username="timeout-host", password_hash="hash")
        db.add_all([game, user])
        await db.commit()
        session = GameSession(
            room_code="TIMEOUT",
            host_id=user.id,
            game_id=game.id,
            name="Timeout",
            capacity=2,
            timeout_minutes=60,
            metrics=[],
            scores={},
            state=SessionState.LIVE,
            deadline=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
        )
        db.add(session)
        await db.commit()
        invalidated = []
        async def record_invalidation(game_id):
            invalidated.append(game_id)

        monkeypatch.setattr(main, "invalidate_leaderboard", record_invalidation)
        await main.session_by_id(db, session.id)

    assert invalidated == [game.id]


def test_compose_waits_for_redis_health():
    import yaml

    with open("docker-compose.yml") as compose_file:
        services = yaml.safe_load(compose_file)["services"]
    assert services["redis"]["healthcheck"]["test"] == ["CMD", "redis-cli", "ping"]
    assert services["backend"]["depends_on"]["redis"]["condition"] == "service_healthy"
    assert "ports" not in services["redis"]
