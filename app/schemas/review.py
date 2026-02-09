"""Review schemas."""
from datetime import datetime
from pydantic import BaseModel


class ReviewCreate(BaseModel):
    album_id: str
    rating: float
    content: str | None = None
    type: str = "review"
    tags: list[str] = []
    share_to_feed: bool = True


class ReviewUpdate(BaseModel):
    rating: float | None = None
    content: str | None = None
    tags: list[str] | None = None
    share_to_feed: bool | None = None


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    album_id: str
    rating: float
    content: str | None
    type: str
    tags: list[str]
    share_to_feed: bool
    created_at: datetime
    likes: int = 0
    comments: int = 0
    user_name: str | None = None
    user_avatar: str | None = None
    album_title: str | None = None
    album_cover: str | None = None

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    user_id: str
    review_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
