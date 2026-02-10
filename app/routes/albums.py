"""Album routes."""
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import func
from app.database import get_db
from app.services.cover_art import fetch_cover_for_album
from app.services.search import search_albums as search_albums_service
from app.models import Album, Track, Review, LogEntry
from app.schemas.album import AlbumCreate, AlbumResponse, AlbumUpdate
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/albums", tags=["albums"])


@router.get("")
def list_albums(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    """List albums (browse catalog). Used when no search query."""
    qry = db.query(Album).order_by(Album.created_at.desc())
    total = qry.count()
    albums = qry.offset(offset).limit(limit).all()
    return {
        "data": [_album_to_dict(a) for a in albums],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/search")
def search_albums(
    q: str = Query(...),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    """Search albums by title/artist. Uses PostgreSQL FTS + trigram fuzzy when available."""
    albums, total = search_albums_service(db, q, limit=limit, offset=offset)
    return {
        "data": [_album_to_dict(a) for a in albums],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _album_to_dict(a: Album, avg_rating=None, total_logs=None):
    d = {
        "id": a.id,
        "title": a.title,
        "artist": a.artist,
        "year": a.year,
        "cover_url": a.cover_url,
        "genres": a.genres or [],
        "label": a.label,
        "length_seconds": a.length_seconds,
        "description": a.description,
        "wikipedia_url": getattr(a, "wikipedia_url", None),
    }
    if avg_rating is not None:
        d["avg_rating"] = avg_rating
    if total_logs is not None:
        d["total_logs"] = total_logs
    return d


@router.get("/trending")
def trending_albums(
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
    return [_album_to_dict(a) for a in albums]


@router.get("/by-genre/{genre}")
def albums_by_genre(
    genre: str,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    all_albums = db.query(Album).all()
    genre_lower = genre.strip().lower()
    matched = [
        a for a in all_albums
        if any(genre_lower in (g or "").lower() for g in (a.genres or []))
    ]
    total = len(matched)
    albums = matched[offset : offset + limit]
    return {
        "data": [_album_to_dict(a) for a in albums],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{album_id}")
def update_album(album_id: str, data: AlbumUpdate, db=Depends(get_db)):
    """Update album fields (e.g. description)."""
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    if data.description is not None:
        album.description = data.description
    db.commit()
    db.refresh(album)
    return _album_to_dict(album)


@router.patch("/{album_id}/cover")
def refresh_album_cover(album_id: str, db=Depends(get_db)):
    """Fetch and update cover art for an album that has none or wrong image."""
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    url = fetch_cover_for_album(album.title, album.artist, album.year)
    if url:
        album.cover_url = url
        db.commit()
        db.refresh(album)
    return _album_to_dict(album)


@router.get("/{album_id}")
def get_album(album_id: str, db=Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    avg = db.query(func.avg(LogEntry.rating)).filter(LogEntry.album_id == album_id).scalar()
    total = db.query(func.count(LogEntry.id)).filter(LogEntry.album_id == album_id).scalar() or 0
    tracks = db.query(Track).filter(Track.album_id == album_id).order_by(Track.number).all()
    d = _album_to_dict(album, avg_rating=float(avg) if avg else None, total_logs=total)
    d["tracks"] = [{"id": t.id, "number": t.number, "title": t.title, "duration": t.duration} for t in tracks]
    d["created_at"] = album.created_at.isoformat() if album.created_at else None
    return d


@router.get("/{album_id}/reviews")
def get_album_reviews(
    album_id: str,
    db=Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    from app.models import Review
    from app.models import User
    from app.models import Like
    from app.models import Comment

    def _to_dict(r):
        likes = db.query(func.count(Like.user_id)).filter(Like.review_id == r.id).scalar() or 0
        comments = db.query(func.count(Comment.id)).filter(Comment.review_id == r.id).scalar() or 0
        u = db.query(User).filter(User.id == r.user_id).first()
        a = db.query(Album).filter(Album.id == r.album_id).first()
        return {
            "id": r.id, "user_id": r.user_id, "album_id": r.album_id,
            "rating": r.rating, "content": r.content, "type": r.type,
            "tags": r.tags or [], "share_to_feed": r.share_to_feed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "likes": likes, "comments": comments,
            "user_name": u.username if u else None,
            "user_avatar": u.avatar_url if u else None,
            "album_title": a.title if a else None,
            "album_cover": a.cover_url if a else None,
        }
    qry = db.query(Review).filter(Review.album_id == album_id)
    total = qry.count()
    reviews = qry.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": [_to_dict(r) for r in reviews], "total": total, "limit": limit, "offset": offset}


@router.get("/{album_id}/ratings-distribution")
def ratings_distribution(album_id: str, db=Depends(get_db)):
    buckets = [(5, 4.5, 5.5), (4, 3.5, 4.5), (3, 2.5, 3.5), (2, 1.5, 2.5), (1, 0.5, 1.5)]
    counts = {}
    for star, lo, hi in buckets:
        c = db.query(func.count(LogEntry.id)).filter(
            LogEntry.album_id == album_id,
            LogEntry.rating >= lo,
            LogEntry.rating < hi,
        ).scalar() or 0
        counts[star] = c
    total = sum(counts.values()) or 1
    return {
        "five": round(100 * counts[5] / total, 1),
        "four": round(100 * counts[4] / total, 1),
        "three": round(100 * counts[3] / total, 1),
        "two": round(100 * counts[2] / total, 1),
        "one": round(100 * counts[1] / total, 1),
    }


@router.post("")
def create_album(
    data: AlbumCreate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    cover_url = data.cover_url
    if not cover_url:
        cover_url = fetch_cover_for_album(data.title, data.artist, data.year)
    album = Album(
        id=generate_id(),
        title=data.title,
        artist=data.artist,
        year=data.year,
        cover_url=cover_url,
        genres=data.genres,
        label=data.label,
        length_seconds=data.length_seconds,
        description=data.description,
    )
    db.add(album)
    db.commit()
    db.refresh(album)
    return _album_to_dict(album)
