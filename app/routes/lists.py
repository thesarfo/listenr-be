"""List routes."""
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models import List, ListAlbum, Album, ListLike
from app.schemas.list import ListCreate, ListUpdate, AddAlbumToList
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/lists", tags=["lists"])


def _list_to_dict(l: List, db, include_albums=False):
    albums_count = db.query(func.count(ListAlbum.id)).filter(ListAlbum.list_id == l.id).scalar() or 0
    likes = db.query(func.count(ListLike.user_id)).filter(ListLike.list_id == l.id).scalar() or 0
    d = {
        "id": l.id,
        "user_id": l.user_id,
        "title": l.title,
        "description": l.description,
        "cover_url": l.cover_url,
        "albums_count": albums_count,
        "likes": likes,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
    if include_albums:
        list_albums = (
            db.query(ListAlbum)
            .options(joinedload(ListAlbum.album))
            .filter(ListAlbum.list_id == l.id)
            .order_by(ListAlbum.position)
            .all()
        )
        d["albums"] = [
            {"id": la.album.id, "title": la.album.title, "artist": la.album.artist, "cover_url": la.album.cover_url}
            for la in list_albums
            if la.album is not None
        ]
    return d


@router.get("")
def get_my_lists(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    lists = db.query(List).filter(List.user_id == user.id).all()
    return [_list_to_dict(l, db) for l in lists]


@router.get("/{list_id}")
def get_list(list_id: str, db=Depends(get_db)):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    return _list_to_dict(l, db, include_albums=True)


@router.post("")
def create_list(
    data: ListCreate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = List(
        id=generate_id(),
        user_id=user.id,
        title=data.title,
        description=data.description,
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return _list_to_dict(l, db)


@router.patch("/{list_id}")
def update_list(
    list_id: str,
    data: ListUpdate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your list")
    if data.title is not None:
        l.title = data.title
    if data.description is not None:
        l.description = data.description
    db.commit()
    db.refresh(l)
    return _list_to_dict(l, db)


@router.delete("/{list_id}")
def delete_list(
    list_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your list")
    # Delete child rows first (FK constraints)
    db.query(ListAlbum).filter(ListAlbum.list_id == list_id).delete()
    db.query(ListLike).filter(ListLike.list_id == list_id).delete()
    db.delete(l)
    db.commit()
    return {"message": "ok"}


@router.post("/{list_id}/albums")
def add_album_to_list(
    list_id: str,
    data: AddAlbumToList,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your list")
    album = db.query(Album).filter(Album.id == data.album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    max_pos = db.query(func.max(ListAlbum.position)).filter(ListAlbum.list_id == list_id).scalar() or 0
    la = ListAlbum(
        id=generate_id(),
        list_id=list_id,
        album_id=data.album_id,
        position=max_pos + 1,
    )
    db.add(la)
    db.commit()
    return {"message": "ok"}


@router.delete("/{list_id}/albums/{album_id}")
def remove_album_from_list(
    list_id: str,
    album_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your list")
    db.query(ListAlbum).filter(ListAlbum.list_id == list_id, ListAlbum.album_id == album_id).delete()
    db.commit()
    return {"message": "ok"}


@router.post("/{list_id}/like")
def like_list(
    list_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    existing = db.query(ListLike).filter(ListLike.user_id == user.id, ListLike.list_id == list_id).first()
    if existing:
        return {"message": "Already liked"}
    like = ListLike(user_id=user.id, list_id=list_id)
    db.add(like)
    db.commit()
    return {"message": "ok"}


@router.delete("/{list_id}/like")
def unlike_list(
    list_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    db.query(ListLike).filter(ListLike.user_id == user.id, ListLike.list_id == list_id).delete()
    db.commit()
    return {"message": "ok"}
