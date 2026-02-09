"""Search routes."""
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.models import Album, User

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(...),
    type: str | None = Query(None, description="albums|artists|users"),
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
):
    q = q.strip()
    if not q:
        return {"albums": [], "users": []}
    result = {"albums": [], "users": []}
    if type is None or type == "albums":
        albums = (
            db.query(Album)
            .filter(
                (Album.title.ilike(f"%{q}%")) | (Album.artist.ilike(f"%{q}%"))
            )
            .limit(limit)
            .all()
        )
        result["albums"] = [
            {"id": a.id, "title": a.title, "artist": a.artist, "cover_url": a.cover_url}
            for a in albums
        ]
    if type is None or type == "users":
        users = (
            db.query(User)
            .filter(User.username.ilike(f"%{q}%"))
            .limit(limit)
            .all()
        )
        result["users"] = [
            {"id": u.id, "username": u.username, "avatar_url": u.avatar_url}
            for u in users
        ]
    return result
