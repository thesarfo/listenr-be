"""Notification routes."""
from fastapi import APIRouter, Depends, Query, HTTPException

from app.database import get_db
from app.models import Notification
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def get_notifications(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    qry = db.query(Notification).filter(Notification.user_id == user.id)
    total = qry.count()
    notifs = qry.order_by(Notification.read.asc(), Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "ref_id": n.ref_id,
                "read": n.read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    db.commit()
    return {"message": "ok"}


@router.patch("/read-all")
def mark_all_read(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    for n in db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False,
    ).all():
        n.read = True
    db.commit()
    return {"message": "ok"}
