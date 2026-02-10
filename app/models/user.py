"""User model."""
from sqlalchemy import Boolean, Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # None for OAuth-only users (new DBs)
    google_id = Column(String(64), unique=True, nullable=True, index=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    reviews = relationship("Review", back_populates="user")
    log_entries = relationship("LogEntry", back_populates="user")
    lists = relationship("List", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
