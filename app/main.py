from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import asyncio
import json
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import SessionLocal, engine, get_session
from .models import AuthSession, Base, GameDefinition, GameSession, Participant, SessionState, User
from .realtime import hub
from .schemas import Credentials, CreateSession, ScoreUpdate
from .security import hash_password, new_session_id, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db_session:
        if not (await db_session.execute(select(GameDefinition).limit(1))).scalar_one_or_none():
            db_session.add_all([
                GameDefinition(name="Catan", default_timeout_minutes=120, ranking_direction="high", metrics=[{"id": "points", "label": "Points"}]),
                GameDefinition(name="Azul", default_timeout_minutes=90, ranking_direction="high", metrics=[{"id": "points", "label": "Points"}]),
            ])
            await db_session.commit()
    yield
    await engine.dispose()


app = FastAPI(title="Game Leaders API", version="0.1.0", lifespan=lifespan)


async def current_user(request: Request, db: AsyncSession = Depends(get_session)) -> User:
    token = request.cookies.get("game_leaders_session")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(select(User).join(AuthSession, AuthSession.user_id == User.id).where(AuthSession.id == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_session(session: GameSession | None) -> GameSession:
    if not session or session.state == SessionState.DISCARDED:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def session_by_id(db: AsyncSession, session_id: str) -> GameSession:
    session = require_session((await db.execute(select(GameSession).where(GameSession.id == session_id))).scalar_one_or_none())
    if session.state == SessionState.LIVE and session.deadline and session.deadline <= datetime.now(timezone.utc).replace(tzinfo=None):
        session.state = SessionState.TIMED_OUT
        session.revision += 1
        await db.commit()
    return session


async def member_ids(db: AsyncSession, session_id: str) -> set[str]:
    result = await db.execute(select(Participant.user_id).where(Participant.session_id == session_id, Participant.active.is_(True)))
    return set(result.scalars())


async def snapshot(db: AsyncSession, session: GameSession) -> dict:
    game = await db.get(GameDefinition, session.game_id)
    participants = await db.execute(select(Participant, User).join(User, User.id == Participant.user_id).where(Participant.session_id == session.id))
    people = [{"user_id": user.id, "username": user.username, "active": participant.active, "scores": session.scores.get(user.id, {})} for participant, user in participants]
    return {"id": session.id, "room_code": session.room_code, "name": session.name, "game_id": session.game_id, "ranking_direction": game.ranking_direction, "host_id": session.host_id, "capacity": session.capacity, "timeout_minutes": session.timeout_minutes, "state": session.state, "metrics": session.metrics, "revision": session.revision, "deadline": session.deadline.isoformat() if session.deadline else None, "participants": people}


async def publish_snapshot(db: AsyncSession, session: GameSession) -> dict:
    value = await snapshot(db, session)
    await hub.publish(session.id, value)
    return value


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
async def register(credentials: Credentials, db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    if (await db.execute(select(User).where(User.username == credentials.username))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=credentials.username, password_hash=hash_password(credentials.password))
    db.add(user)
    await db.commit()
    return {"username": user.username}


@app.post("/auth/login")
async def login(credentials: Credentials, response: Response, db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    user = (await db.execute(select(User).where(User.username == credentials.username))).scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = new_session_id()
    db.add(AuthSession(id=token, user_id=user.id))
    await db.commit()
    response.set_cookie("game_leaders_session", token, httponly=True, samesite="lax", secure=False, max_age=60 * 60 * 24 * 30)
    return {"username": user.username}


@app.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    token = request.cookies.get("game_leaders_session")
    if token:
        await db.execute(delete(AuthSession).where(AuthSession.id == token))
        await db.commit()
    response.delete_cookie("game_leaders_session")
    return {"status": "ok"}


@app.get("/auth/me")
async def me(user: User = Depends(current_user)) -> dict[str, str]:
    return {"id": user.id, "username": user.username}


@app.get("/games")
async def games(_: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    definitions = (await db.execute(select(GameDefinition).order_by(GameDefinition.name))).scalars()
    return [{"id": game.id, "name": game.name, "default_timeout_minutes": game.default_timeout_minutes, "ranking_direction": game.ranking_direction, "metrics": game.metrics} for game in definitions]


@app.post("/sessions", status_code=201)
async def create_session(payload: CreateSession, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    active = await db.execute(select(GameSession).where(GameSession.host_id == user.id, GameSession.state.in_([SessionState.SETUP, SessionState.LIVE, SessionState.TIMED_OUT])))
    if active.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Host already has an active session")
    game = (await db.execute(select(GameDefinition).where(GameDefinition.id == payload.game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    metrics = payload.metrics or game.metrics
    if not metrics:
        raise HTTPException(status_code=400, detail="At least one scoring metric is required")
    code = None
    while not code:
        candidate = secrets.token_hex(3).upper()
        if not (await db.execute(select(GameSession).where(GameSession.room_code == candidate))).scalar_one_or_none():
            code = candidate
    session = GameSession(room_code=code, host_id=user.id, game_id=game.id, name=f"{user.username}'s game room", capacity=payload.capacity, timeout_minutes=payload.timeout_minutes or game.default_timeout_minutes, metrics=metrics, scores={})
    db.add(session)
    await db.flush()
    db.add(Participant(session_id=session.id, user_id=user.id))
    await db.commit()
    return await snapshot(db, session)


@app.get("/sessions/recent")
async def recent_sessions(_: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await db.execute(select(GameSession).where(GameSession.state.in_([SessionState.SETUP, SessionState.LIVE, SessionState.TIMED_OUT])).order_by(GameSession.created_at.desc()).limit(20))).scalars()
    return [{"id": s.id, "name": s.name, "room_code": s.room_code, "game_id": s.game_id, "capacity": s.capacity, "state": s.state} for s in rows]


async def find_session(db: AsyncSession, key: str) -> GameSession:
    result = await db.execute(select(GameSession).where((GameSession.id == key) | (GameSession.room_code == key.upper()) | (GameSession.name.ilike(f"%{key}%"))))
    return require_session(result.scalars().first())


@app.get("/sessions/{key}")
async def get_session_details(key: str, _: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    return await snapshot(db, await find_session(db, key))


@app.post("/sessions/{session_id}/join")
async def join_session(session_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    session = await session_by_id(db, session_id)
    if session.state == SessionState.FINALIZED:
        raise HTTPException(status_code=409, detail="Session is finalized")
    participants = await member_ids(db, session.id)
    if user.id not in participants and len(participants) >= session.capacity:
        raise HTTPException(status_code=409, detail="Session is full")
    if user.id not in participants:
        existing = (await db.execute(select(Participant).where(Participant.session_id == session.id, Participant.user_id == user.id))).scalar_one_or_none()
        if existing:
            existing.active = True
        else:
            db.add(Participant(session_id=session.id, user_id=user.id))
        await db.commit()
    return await publish_snapshot(db, session)


@app.post("/sessions/{session_id}/leave")
async def leave_session(session_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    session = await session_by_id(db, session_id)
    participant = (await db.execute(select(Participant).where(Participant.session_id == session.id, Participant.user_id == user.id))).scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Not a participant")
    participant.active = False
    await db.commit()
    return await publish_snapshot(db, session)


@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    session = await session_by_id(db, session_id)
    if session.host_id != user.id:
        raise HTTPException(status_code=403, detail="Host only")
    if session.state != SessionState.SETUP:
        raise HTTPException(status_code=409, detail="Session cannot be started")
    session.state = SessionState.LIVE
    session.deadline = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=session.timeout_minutes)
    await db.commit()
    return await publish_snapshot(db, session)


@app.post("/sessions/{session_id}/scores/{user_id}")
async def update_score(session_id: str, user_id: str, update: ScoreUpdate, actor: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    session = await session_by_id(db, session_id)
    if session.state not in [SessionState.LIVE, SessionState.TIMED_OUT]:
        raise HTTPException(status_code=409, detail="Scores are not editable")
    if actor.id != user_id and actor.id != session.host_id:
        raise HTTPException(status_code=403, detail="Participants may edit only their own scores")
    if user_id not in await member_ids(db, session.id):
        raise HTTPException(status_code=404, detail="Participant not found")
    if update.metric not in {metric["id"] for metric in session.metrics}:
        raise HTTPException(status_code=400, detail="Unknown scoring metric")
    scores = dict(session.scores)
    scores[user_id] = {**scores.get(user_id, {}), update.metric: update.value}
    session.scores = scores
    session.revision += 1
    await db.commit()
    return await publish_snapshot(db, session)


@app.post("/sessions/{session_id}/finalize")
async def finalize_session(session_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    session = await session_by_id(db, session_id)
    if session.host_id != user.id:
        raise HTTPException(status_code=403, detail="Host only")
    if session.state == SessionState.DISCARDED:
        raise HTTPException(status_code=404, detail="Session not found")
    session.state = SessionState.FINALIZED
    await db.commit()
    return await publish_snapshot(db, session)


@app.post("/sessions/{session_id}/discard")
async def discard_session(session_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    session = await session_by_id(db, session_id)
    if session.host_id != user.id:
        raise HTTPException(status_code=403, detail="Host only")
    session.state = SessionState.DISCARDED
    await db.commit()
    await hub.publish(session.id, {"id": session.id, "state": SessionState.DISCARDED})
    return {"status": "discarded"}


@app.get("/sessions/{session_id}/events")
async def events(session_id: str, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> StreamingResponse:
    session = await session_by_id(db, session_id)
    if user.id not in await member_ids(db, session.id) and user.id != session.host_id:
        raise HTTPException(status_code=403, detail="Session membership required")
    queue = hub.subscribe(session.id)
    initial = await snapshot(db, session)

    async def stream():
        try:
            yield f"event: snapshot\ndata: {json.dumps(initial)}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    value = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: snapshot\ndata: {json.dumps(value)}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            hub.unsubscribe(session.id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/leaderboards/{game_id}")
async def leaderboard(game_id: str, _: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    game = (await db.execute(select(GameDefinition).where(GameDefinition.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return await build_leaderboard(db, {game_id: game}, sort_descending=game.ranking_direction == "high", include_session_id=True)


@app.get("/leaderboards")
async def global_leaderboard(_: User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    games = {game.id: game for game in (await db.execute(select(GameDefinition))).scalars()}
    return await build_leaderboard(db, games, sort_descending=True, include_session_id=False)


async def build_leaderboard(db: AsyncSession, games: dict[str, GameDefinition], sort_descending: bool, include_session_id: bool) -> list[dict]:
    sessions = (await db.execute(select(GameSession).where(GameSession.state.in_([SessionState.TIMED_OUT, SessionState.FINALIZED])))).scalars()
    best: dict[tuple[str, str], dict] = {}
    games_played: dict[str, int] = {}
    for session in sessions:
        game = games.get(session.game_id)
        if not game:
            continue
        for user_id, values in session.scores.items():
            games_played[user_id] = games_played.get(user_id, 0) + 1
            total = sum(float(value) for value in values.values())
            key = (session.game_id, user_id)
            current = best.get(key)
            if current is None or (game.ranking_direction == "high" and total > current["score"]) or (game.ranking_direction == "low" and total < current["score"]):
                best[key] = {"user_id": user_id, "score": total, "session_id": session.id}
    totals: dict[str, float] = {}
    for (_, user_id), value in best.items():
        totals[user_id] = totals.get(user_id, 0) + value["score"]
    users = {user.id: user.username for user in (await db.execute(select(User).where(User.id.in_(totals.keys())))).scalars()}
    session_ids = {user_id: value["session_id"] for (game_id, user_id), value in best.items() if game_id in games}
    rows = [{"user_id": user_id, "username": users.get(user_id), "score": total, "session_id": session_ids.get(user_id) if include_session_id else None, "games_played": games_played.get(user_id, 0)} for user_id, total in totals.items()]
    rows.sort(key=lambda row: row["score"], reverse=sort_descending)
    rank = 0
    previous = None
    for index, row in enumerate(rows, start=1):
        if row["score"] != previous:
            rank = index
            previous = row["score"]
        row["rank"] = rank
    return rows
