"""Review, LogEntry, Comment, Like models."""
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, TEXT

from app.models.base import Base


class JSONList(TypeDecorator):
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value or []


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    rating = Column(Float, nullable=False)
    content = Column(Text, nullable=True)
    type = Column(String(16), nullable=False, default="review")
    tags = Column(JSONList, nullable=False, default=list)
    share_to_feed = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="reviews")
    album = relationship("Album", back_populates="reviews")
    likes_rel = relationship("Like", back_populates="review")
    comments_rel = relationship("Comment", back_populates="review")


class LogEntry(Base):
    """Listening diary entry."""
    __tablename__ = "log_entries"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    rating = Column(Float, nullable=False)
    content = Column(Text, nullable=True)
    format = Column(String(32), nullable=True, default="digital")
    tags = Column(JSONList, nullable=False, default=list)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="log_entries")
    album = relationship("Album", back_populates="log_entries")


class Like(Base):
    __tablename__ = "likes"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    review = relationship("Review", back_populates="likes_rel")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="comments")
    review = relationship("Review", back_populates="comments_rel")
