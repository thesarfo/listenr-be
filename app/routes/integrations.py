"""Integration routes (Spotify, Apple Music)."""
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import Integration
from app.middleware.auth import get_current_user_required

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/spotify/import")
def spotify_import(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    return {"message": "Spotify import stub - OAuth flow required"}


@router.post("/apple/import")
def apple_import(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    return {"message": "Apple Music import stub - OAuth flow required"}


@router.get("/status")
def get_status(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    spotify = db.query(Integration).filter(
        Integration.user_id == user.id,
        Integration.provider == "spotify",
    ).first()
    apple = db.query(Integration).filter(
        Integration.user_id == user.id,
        Integration.provider == "apple",
    ).first()
    return {
        "spotify": bool(spotify),
        "apple": bool(apple),
        "spotify_last_sync": spotify.last_sync_at.isoformat() if spotify and spotify.last_sync_at else None,
        "apple_last_sync": apple.last_sync_at.isoformat() if apple and apple.last_sync_at else None,
    }
