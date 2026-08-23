import pytest
import json
import hashlib

from app.db import SessionLocal
from app.models import GameDefinition, GameSession, SessionState


async def register_and_login(client, username):
    await client.post("/auth/register", json={"username": username, "password": "correct horse battery"})
    response = await client.post("/auth/login", json={"username": username, "password": "correct horse battery"})
    assert response.status_code == 200


def etag_of(body: list[dict]) -> str:
    return '"' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32] + '"'


@pytest.mark.asyncio
async def test_auth_and_score_authorization(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Test Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "host")
    created = await client.post("/sessions", json={"game_id": game_id, "capacity": 3})
    assert created.status_code == 201
    session = created.json()
    await client.post(f"/sessions/{session['id']}/start")
    own_id = (await client.get("/auth/me")).json()["id"]
    changed = await client.post(f"/sessions/{session['id']}/scores/{own_id}", json={"metric": "points", "value": 42})
    assert changed.status_code == 200

    await register_and_login(client, "player")
    joined = await client.post(f"/sessions/{session['id']}/join")
    assert joined.status_code == 200
    player_id = (await client.get("/auth/me")).json()["id"]
    assert (await client.post(f"/sessions/{session['id']}/scores/{own_id}", json={"metric": "points", "value": 10})).status_code == 403
    assert (await client.post(f"/sessions/{session['id']}/scores/{player_id}", json={"metric": "points", "value": 10})).status_code == 200


@pytest.mark.asyncio
async def test_finalize_and_best_leaderboard(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Rank Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "winner")
    user_id = (await client.get("/auth/me")).json()["id"]
    first = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{first['id']}/start")
    await client.post(f"/sessions/{first['id']}/scores/{user_id}", json={"metric": "points", "value": 25})
    await client.post(f"/sessions/{first['id']}/finalize")
    board = await client.get(f"/leaderboards/{game_id}")
    assert board.json()[0]["score"] == 25
    assert board.json()[0]["session_id"] == first["id"]


@pytest.mark.asyncio
async def test_leave_and_rejoin_reactivates_membership(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Rejoin Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "host")
    created = (await client.post("/sessions", json={"game_id": game_id, "capacity": 3})).json()
    await register_and_login(client, "player")
    await client.post(f"/sessions/{created['id']}/join")
    await client.post(f"/sessions/{created['id']}/leave")
    rejoined = await client.post(f"/sessions/{created['id']}/join")
    assert rejoined.status_code == 200
    participants = rejoined.json()["participants"]
    assert len(participants) == 2
    assert len([p for p in participants if p["active"]]) == 2


@pytest.mark.asyncio
async def test_events_stream_requires_active_membership(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Stream Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "owner")
    created = (await client.post("/sessions", json={"game_id": game_id, "capacity": 3})).json()
    await register_and_login(client, "outsider")
    response = await client.get(f"/sessions/{created['id']}/events")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_session_snapshot_exposes_game_ranking_direction(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Low Wins", default_timeout_minutes=60, ranking_direction="low", metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "low_player")
    created = await client.post("/sessions", json={"game_id": game_id, "capacity": 2})

    assert created.json()["ranking_direction"] == "low"


@pytest.mark.asyncio
async def test_leaderboard_is_public_no_auth_required(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Public Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    response = await client.get(f"/leaderboards/{game_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_cache_headers_present(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Cache Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    response = await client.get(f"/leaderboards/{game_id}")
    assert "Cache-Control" in response.headers
    assert "public" in response.headers["Cache-Control"]
    assert "max-age=30" in response.headers["Cache-Control"]
    assert "stale-while-revalidate=60" in response.headers["Cache-Control"]
    assert "ETag" in response.headers


@pytest.mark.asyncio
async def test_etag_matches_response_body(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Etag Game", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "etag_player")
    user_id = (await client.get("/auth/me")).json()["id"]
    session = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session['id']}/start")
    await client.post(f"/sessions/{session['id']}/scores/{user_id}", json={"metric": "points", "value": 42})
    await client.post(f"/sessions/{session['id']}/finalize")
    response = await client.get(f"/leaderboards/{game_id}")
    expected_etag = etag_of(response.json())
    assert response.headers["ETag"] == expected_etag


@pytest.mark.asyncio
async def test_cache_invalidation_on_score_update(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Inval Game", default_timeout_minutes=60, ranking_direction="low", metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "scorer")
    user_id = (await client.get("/auth/me")).json()["id"]

    session1 = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session1['id']}/start")
    await client.post(f"/sessions/{session1['id']}/scores/{user_id}", json={"metric": "points", "value": 100})
    await client.post(f"/sessions/{session1['id']}/finalize")

    board1 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert board1[0]["score"] == 100

    session2 = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session2['id']}/start")
    await client.post(f"/sessions/{session2['id']}/scores/{user_id}", json={"metric": "points", "value": 5})
    await client.post(f"/sessions/{session2['id']}/finalize")

    board2 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert board2[0]["score"] == 5


@pytest.mark.asyncio
async def test_cache_invalidation_on_finalize(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Fin Inval", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "finalizer")
    user_id = (await client.get("/auth/me")).json()["id"]
    session = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session['id']}/start")
    await client.post(f"/sessions/{session['id']}/scores/{user_id}", json={"metric": "points", "value": 30})

    board1 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert len(board1) == 0

    await client.post(f"/sessions/{session['id']}/finalize")

    board2 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert len(board2) == 1
    assert board2[0]["score"] == 30


@pytest.mark.asyncio
async def test_cache_invalidation_on_discard(client):
    async with SessionLocal() as db:
        game = GameDefinition(name="Disc Inval", default_timeout_minutes=60, metrics=[{"id": "points", "label": "Points"}])
        db.add(game)
        await db.commit()
        game_id = game.id
    await register_and_login(client, "discarder")
    user_id = (await client.get("/auth/me")).json()["id"]
    session = (await client.post("/sessions", json={"game_id": game_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session['id']}/start")
    await client.post(f"/sessions/{session['id']}/scores/{user_id}", json={"metric": "points", "value": 50})
    await client.post(f"/sessions/{session['id']}/finalize")

    board1 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert len(board1) == 1

    await client.post(f"/sessions/{session['id']}/discard")

    board2 = (await client.get(f"/leaderboards/{game_id}")).json()
    assert len(board2) == 0


@pytest.mark.asyncio
async def test_global_leaderboard_endpoint_removed(client):
    response = await client.get("/leaderboards")
    assert response.status_code in [404, 405]


@pytest.mark.asyncio
async def test_leaderboard_events_404_for_unknown_game(client):
    resp = await client.get("/leaderboards/does-not-exist/events")
    assert resp.status_code == 404
