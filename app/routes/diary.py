"""Diary (LogEntry) routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models import LogEntry, Album, User
from app.schemas.diary import LogEntryCreate, LogEntryUpdate
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/diary", tags=["diary"])


def _entry_to_dict(e: LogEntry, db):
    a = db.query(Album).filter(Album.id == e.album_id).first()
    return {
        "id": e.id,
        "user_id": e.user_id,
        "album_id": e.album_id,
        "rating": e.rating,
        "content": e.content,
        "format": e.format,
        "tags": e.tags or [],
        "logged_at": e.logged_at.isoformat() if e.logged_at else None,
        "album_title": a.title if a else None,
        "album_artist": a.artist if a else None,
        "album_cover": a.cover_url if a else None,
    }


@router.get("/export")
def export_diary(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
    format: str = Query("json", description="json|csv"),
):
    entries = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user.id)
        .order_by(LogEntry.logged_at.desc())
        .all()
    )
    data = [_entry_to_dict(e, db) for e in entries]
    if format == "csv":
        import csv
        from io import StringIO
        output = StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(output.getvalue(), media_type="text/csv")
    return {"data": data}


@router.get("")
def get_diary(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
    month: str | None = None,
    rating_min: float | None = None,
    format: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    qry = db.query(LogEntry).filter(LogEntry.user_id == user.id)
    if month:
        try:
            year, month_num = map(int, month.split("-"))
            from datetime import date
            start = datetime(year, month_num, 1)
            if month_num == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month_num + 1, 1)
            qry = qry.filter(LogEntry.logged_at >= start, LogEntry.logged_at < end)
        except (ValueError, IndexError):
            pass
    if rating_min is not None:
        qry = qry.filter(LogEntry.rating >= rating_min)
    if format:
        qry = qry.filter(LogEntry.format == format)
    total = qry.count()
    entries = qry.order_by(LogEntry.logged_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [_entry_to_dict(e, db) for e in entries],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("")
def create_entry(
    data: LogEntryCreate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    e = LogEntry(
        id=generate_id(),
        user_id=user.id,
        album_id=data.album_id,
        rating=data.rating,
        content=data.content,
        format=data.format,
        tags=data.tags,
        logged_at=data.logged_at or datetime.utcnow(),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _entry_to_dict(e, db)


@router.patch("/{entry_id}")
def update_entry(
    entry_id: str,
    data: LogEntryUpdate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    e = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    if e.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your entry")
    if data.rating is not None:
        e.rating = data.rating
    if data.content is not None:
        e.content = data.content
    if data.format is not None:
        e.format = data.format
    if data.tags is not None:
        e.tags = data.tags
    db.commit()
    db.refresh(e)
    return _entry_to_dict(e, db)


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    e = db.query(LogEntry).filter(LogEntry.id == entry_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    if e.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your entry")
    db.delete(e)
    db.commit()
    return {"message": "ok"}
