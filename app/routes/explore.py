"""Explore routes."""
from fastapi import APIRouter, Depends, Query

from sqlalchemy import func
from app.database import get_db
from app.models import Album, LogEntry, Follow, Review
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/explore", tags=["explore"])


def _album_brief(a):
    return {
        "id": a.id,
        "title": a.title,
        "artist": a.artist,
        "year": a.year,
        "cover_url": a.cover_url,
        "genres": a.genres or [],
    }


@router.get("/trending")
def trending(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
):
    """Albums recently released (by year, newest first)."""
    albums = (
        db.query(Album)
        .order_by(Album.year.desc().nullslast(), Album.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_album_brief(a) for a in albums]


@router.get("/popular")
def popular(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
):
    """Albums with the most reviews."""
    subq = (
        db.query(Review.album_id, func.count(Review.id).label("cnt"))
        .group_by(Review.album_id)
        .subquery()
    )
    albums = (
        db.query(Album)
        .join(subq, Album.id == subq.c.album_id)
        .order_by(subq.c.cnt.desc())
        .limit(limit)
        .all()
    )
    if not albums:
        albums = db.query(Album).order_by(Album.created_at.desc()).limit(limit).all()
    return [_album_brief(a) for a in albums]


@router.get("/popular-with-friends")
def popular_with_friends(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    if not user:
        return popular(limit=limit, db=db)
    following = db.query(Follow.following_id).filter(Follow.follower_id == user.id).subquery()
    subq = (
        db.query(LogEntry.album_id, func.count(LogEntry.id).label("cnt"))
        .filter(LogEntry.user_id.in_(following))
        .group_by(LogEntry.album_id)
        .subquery()
    )
    albums = (
        db.query(Album)
        .join(subq, Album.id == subq.c.album_id)
        .order_by(subq.c.cnt.desc())
        .limit(limit)
        .all()
    )
    if not albums:
        # Fallback: show random/recent albums when friends haven't logged yet
        albums = db.query(Album).order_by(Album.created_at.desc()).limit(limit).all()
    return [_album_brief(a) for a in albums]


@router.get("/genres")
def get_genres(db=Depends(get_db)):
    albums = db.query(Album).all()
    genres = set()
    for a in albums:
        for g in (a.genres or []):
            genres.add(g)
    return sorted(genres)


@router.post("/ai-discovery")
def ai_discovery_route(body: dict):
    from app.services.ai import discovery
    query = body.get("query", "")
    result = discovery(query)
    return {"result": result}
