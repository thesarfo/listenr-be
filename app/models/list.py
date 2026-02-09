"""List, ListAlbum, and ListCollaborator models."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ListCollaborator(Base):
    """User who can edit a list (in addition to owner)."""
    __tablename__ = "list_collaborators"
    __table_args__ = (UniqueConstraint("list_id", "user_id", name="uq_list_collaborator"),)

    list_id = Column(String(36), ForeignKey("lists.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    list = relationship("List", back_populates="collaborators")
    user = relationship("User", backref="collaborating_lists")


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
    collaborators = relationship("ListCollaborator", back_populates="list", cascade="all, delete-orphan")


class ListAlbum(Base):
    __tablename__ = "list_albums"

    id = Column(String(36), primary_key=True, index=True)
    list_id = Column(String(36), ForeignKey("lists.id"), nullable=False)
    album_id = Column(String(36), ForeignKey("albums.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    list = relationship("List", back_populates="list_albums")
    album = relationship("Album", foreign_keys=[album_id], lazy="joined")
