from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class GameOut(BaseModel):
    id: str
    name: str
    default_timeout_minutes: int
    ranking_direction: str
    metrics: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class CreateSession(BaseModel):
    game_id: str
    capacity: int = Field(ge=2, le=20)
    timeout_minutes: int | None = Field(default=None, ge=5, le=1440)
    metrics: list[dict[str, Any]] | None = None


class ScoreUpdate(BaseModel):
    metric: str
    value: float


class SessionAction(BaseModel):
    pass
