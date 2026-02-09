"""User schemas."""
from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    avatar_url: str | None = None
    bio: str | None = None


class UserCreate(UserBase):
    email: str
    password: str


class UserResponse(UserBase):
    id: str
    email: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileResponse(UserResponse):
    albums_count: int = 0
    reviews_count: int = 0
    lists_count: int = 0


class UserUpdate(BaseModel):
    avatar_url: str | None = None
    bio: str | None = None


class FavoriteAlbumUpdate(BaseModel):
    album_ids: list[str]


class FavoriteAlbumResponse(BaseModel):
    id: str
    title: str
    artist: str
    year: int | None
    cover_url: str | None
    genres: list[str] = []
