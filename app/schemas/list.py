"""List schemas."""
from datetime import datetime
from pydantic import BaseModel


class ListCreate(BaseModel):
    title: str
    description: str | None = None


class ListUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ListResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None
    cover_url: str | None
    albums_count: int = 0
    likes: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ListDetailResponse(ListResponse):
    albums: list = []


class AddAlbumToList(BaseModel):
    album_id: str


class AddCollaborator(BaseModel):
    username: str
