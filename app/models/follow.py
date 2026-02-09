"""Follow and FavoriteAlbum models."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (PrimaryKeyConstraint("follower_id", "following_id"),)

    follower_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    following_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FavoriteAlbum(Base):
    __tablename__ = "favorite_albums"
    __table_args__ = (PrimaryKeyConstraint("user_id", "album_id"),)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ListLike(Base):
    """Like on a list."""
    __tablename__ = "list_likes"
    __table_args__ = (PrimaryKeyConstraint("user_id", "list_id"),)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    list_id = Column(String(36), ForeignKey("lists.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
