import pytest

from app.db import SessionLocal
from app.models import GameDefinition


async def register_and_login(client, username):
    await client.post("/auth/register", json={"username": username, "password": "correct horse battery"})
    response = await client.post("/auth/login", json={"username": username, "password": "correct horse battery"})
    assert response.status_code == 200


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

