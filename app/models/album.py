"""Album and Track models."""
import json
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, TEXT

from app.models.base import Base


class JSONList(TypeDecorator):
    """Store Python list as JSON string."""
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value or []


class Album(Base):
    __tablename__ = "albums"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    artist = Column(String(512), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    cover_url = Column(String(512), nullable=True)
    genres = Column(JSONList, nullable=False, default=list)
    label = Column(String(256), nullable=True)
    length_seconds = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    wikipedia_url = Column(String(512), nullable=True)
    spotify_id = Column(String(64), nullable=True, index=True)
    apple_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tracks = relationship("Track", back_populates="album", order_by="Track.number")
    reviews = relationship("Review", back_populates="album")
    log_entries = relationship("LogEntry", back_populates="album")


class Track(Base):
    __tablename__ = "tracks"

    id = Column(String(36), primary_key=True, index=True)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    duration = Column(String(16), nullable=True)

    album = relationship("Album", back_populates="tracks")
