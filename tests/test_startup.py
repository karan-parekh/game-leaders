import pytest

from app.db import SessionLocal
from app.main import app, lifespan
from app.models import GameDefinition


@pytest.mark.asyncio
async def test_startup_succeeds_when_multiple_game_definitions_exist():
    async with SessionLocal() as db:
        db.add_all([
            GameDefinition(name="Catan", default_timeout_minutes=120, metrics=[{"id": "points", "label": "Points"}]),
            GameDefinition(name="Azul", default_timeout_minutes=90, metrics=[{"id": "points", "label": "Points"}]),
        ])
        await db.commit()

    async with lifespan(app):
        pass
