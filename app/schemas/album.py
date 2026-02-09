"""Album schemas."""
from datetime import datetime
from pydantic import BaseModel


class TrackSchema(BaseModel):
    id: str
    number: int
    title: str
    duration: str | None

    model_config = {"from_attributes": True}


class AlbumBase(BaseModel):
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None
    genres: list[str] = []
    label: str | None = None
    length_seconds: int | None = None
    description: str | None = None


class AlbumCreate(AlbumBase):
    pass


class AlbumUpdate(BaseModel):
    description: str | None = None


class AlbumResponse(AlbumBase):
    id: str
    created_at: datetime
    tracks: list[TrackSchema] = []
    avg_rating: float | None = None
    total_logs: int = 0

    model_config = {"from_attributes": True}


class AlbumSearchParams(BaseModel):
    q: str
    limit: int = 20
    offset: int = 0


class RatingsDistribution(BaseModel):
    five: float
    four: float
    three: float
    two: float
    one: float
