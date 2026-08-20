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
async def test_global_leaderboard_aggregates_best_scores_across_games(client):
    async with SessionLocal() as db:
        game_a = GameDefinition(name="Game A", default_timeout_minutes=60, ranking_direction="high", metrics=[{"id": "points", "label": "Points"}])
        game_b = GameDefinition(name="Game B", default_timeout_minutes=60, ranking_direction="high", metrics=[{"id": "points", "label": "Points"}])
        db.add_all([game_a, game_b])
        await db.commit()
        game_a_id, game_b_id = game_a.id, game_b.id
    await register_and_login(client, "champion")
    user_id = (await client.get("/auth/me")).json()["id"]
    for score in (10, 25):
        session = (await client.post("/sessions", json={"game_id": game_a_id, "capacity": 2})).json()
        await client.post(f"/sessions/{session['id']}/start")
        await client.post(f"/sessions/{session['id']}/scores/{user_id}", json={"metric": "points", "value": score})
        await client.post(f"/sessions/{session['id']}/finalize")
    session = (await client.post("/sessions", json={"game_id": game_b_id, "capacity": 2})).json()
    await client.post(f"/sessions/{session['id']}/start")
    await client.post(f"/sessions/{session['id']}/scores/{user_id}", json={"metric": "points", "value": 40})
    await client.post(f"/sessions/{session['id']}/finalize")

    board = (await client.get("/leaderboards")).json()
    assert board[0]["username"] == "champion"
    assert board[0]["score"] == 65
    assert board[0]["games_played"] == 3
