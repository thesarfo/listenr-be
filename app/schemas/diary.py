"""Diary (LogEntry) schemas."""
from datetime import datetime
from pydantic import BaseModel


class LogEntryCreate(BaseModel):
    album_id: str
    rating: float
    content: str | None = None
    format: str = "digital"
    tags: list[str] = []
    logged_at: datetime | None = None


class LogEntryUpdate(BaseModel):
    rating: float | None = None
    content: str | None = None
    format: str | None = None
    tags: list[str] | None = None


class LogEntryResponse(BaseModel):
    id: str
    user_id: str
    album_id: str
    rating: float
    content: str | None
    format: str | None
    tags: list[str]
    logged_at: datetime
    album_title: str | None = None
    album_artist: str | None = None
    album_cover: str | None = None

    model_config = {"from_attributes": True}
