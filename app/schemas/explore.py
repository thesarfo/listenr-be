"""Explore and AI schemas."""
from pydantic import BaseModel


class AIDiscoveryRequest(BaseModel):
    query: str


class AIAlbumInsightRequest(BaseModel):
    album_id: str


class AIPolishReviewRequest(BaseModel):
    content: str
