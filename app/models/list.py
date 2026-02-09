"""List and ListAlbum models."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class List(Base):
    __tablename__ = "lists"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    cover_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="lists")
    list_albums = relationship("ListAlbum", back_populates="list", order_by="ListAlbum.position")


class ListAlbum(Base):
    __tablename__ = "list_albums"

    id = Column(String(36), primary_key=True, index=True)
    list_id = Column(String(36), ForeignKey("lists.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    list = relationship("List", back_populates="list_albums")
    album = relationship("Album", foreign_keys=[album_id], lazy="joined")
