"""AI routes."""
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import Album
from app.schemas.explore import AIDiscoveryRequest, AIAlbumInsightRequest, AIPolishReviewRequest
from app.services import ai as ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/discovery")
def ai_discovery_route(body: AIDiscoveryRequest):
    result = ai_service.discovery(body.query)
    return {"result": result}


@router.post("/album-insight")
def album_insight_route(body: AIAlbumInsightRequest, db=Depends(get_db)):
    album = db.query(Album).filter(Album.id == body.album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    result = ai_service.album_insight(album.title, album.artist)
    return {"result": result}


@router.post("/polish-review")
def polish_review_route(body: AIPolishReviewRequest):
    result = ai_service.polish_review(body.content)
    return {"result": result}
