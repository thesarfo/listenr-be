"""Search routes."""
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.services.search import search_albums as search_albums_service, search_users as search_users_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(...),
    type: str | None = Query(None, description="albums|artists|users"),
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
):
    """Global search: albums and users. Uses PostgreSQL FTS + trigram when available."""
    result = {"albums": [], "users": []}
    if not q.strip():
        return result
    if type is None or type == "albums":
        albums, _ = search_albums_service(db, q, limit=limit, offset=0)
        result["albums"] = [
            {"id": a.id, "title": a.title, "artist": a.artist, "cover_url": a.cover_url}
            for a in albums
        ]
    if type is None or type == "users":
        users, _ = search_users_service(db, q, limit=limit, offset=0)
        result["users"] = [
            {"id": u.id, "username": u.username, "avatar_url": u.avatar_url}
            for u in users
        ]
    return result
