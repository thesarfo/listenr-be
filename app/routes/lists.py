"""List routes."""
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models import List, ListAlbum, Album, ListLike, ListCollaborator, User, Notification
from app.schemas.list import ListCreate, ListUpdate, AddAlbumToList, AddCollaborator
from app.middleware.auth import get_current_user, get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/lists", tags=["lists"])


def _can_edit_list(l: List, user, db) -> bool:
    """Check if user is owner or collaborator."""
    if not user:
        return False
    if l.user_id == user.id:
        return True
    return db.query(ListCollaborator).filter(
        ListCollaborator.list_id == l.id,
        ListCollaborator.user_id == user.id,
    ).first() is not None


def _list_to_dict(l: List, db, include_albums=False, include_collaborators=False, include_preview_albums=False, current_user_id: str | None = None):
    from app.models import User
    albums_count = db.query(func.count(ListAlbum.id)).filter(ListAlbum.list_id == l.id).scalar() or 0
    likes = db.query(func.count(ListLike.user_id)).filter(ListLike.list_id == l.id).scalar() or 0
    owner = db.query(User).filter(User.id == l.user_id).first()
    user_liked = False
    if current_user_id:
        user_liked = db.query(ListLike).filter(
            ListLike.list_id == l.id,
            ListLike.user_id == current_user_id,
        ).first() is not None
    d = {
        "id": l.id,
        "user_id": l.user_id,
        "owner_username": owner.username if owner else None,
        "title": l.title,
        "description": l.description,
        "cover_url": l.cover_url,
        "albums_count": albums_count,
        "likes": likes,
        "user_liked": user_liked if current_user_id else False,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
    if include_preview_albums:
        list_albums = (
            db.query(ListAlbum)
            .options(joinedload(ListAlbum.album))
            .filter(ListAlbum.list_id == l.id)
            .order_by(ListAlbum.position)
            .limit(4)
            .all()
        )
        d["preview_albums"] = [
            {"id": la.album.id, "title": la.album.title, "artist": la.album.artist, "cover_url": la.album.cover_url}
            for la in list_albums
            if la.album is not None
        ]
    if include_collaborators:
        collabs = (
            db.query(User)
            .join(ListCollaborator, ListCollaborator.user_id == User.id)
            .filter(ListCollaborator.list_id == l.id)
            .all()
        )
        d["collaborators"] = [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in collabs]
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
    """Lists owned by user + lists where user is collaborator."""
    collab_list_ids = db.query(ListCollaborator.list_id).filter(ListCollaborator.user_id == user.id).subquery()
    lists = db.query(List).filter(or_(List.user_id == user.id, List.id.in_(collab_list_ids))).all()
    return [_list_to_dict(l, db, include_preview_albums=True, current_user_id=user.id) for l in lists]


@router.get("/liked")
def get_liked_lists(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    """Lists the current user has liked."""
    liked_list_ids = db.query(ListLike.list_id).filter(ListLike.user_id == user.id).subquery()
    lists = db.query(List).filter(List.id.in_(liked_list_ids)).all()
    return [_list_to_dict(l, db, include_preview_albums=True, current_user_id=user.id) for l in lists]


@router.get("/{list_id}")
def get_list(
    list_id: str,
    db=Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get list by ID. Public - no auth required (for shareable links)."""
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    return _list_to_dict(
        l, db,
        include_albums=True,
        include_collaborators=True,
        current_user_id=current_user.id if current_user else None,
    )


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
    if not _can_edit_list(l, user, db):
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
        raise HTTPException(status_code=403, detail="Only the owner can delete the list")
    # Delete child rows first (FK constraints)
    db.query(ListAlbum).filter(ListAlbum.list_id == list_id).delete()
    db.query(ListLike).filter(ListLike.list_id == list_id).delete()
    db.query(ListCollaborator).filter(ListCollaborator.list_id == list_id).delete()
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
    if not _can_edit_list(l, user, db):
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
    if not _can_edit_list(l, user, db):
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
    if l.user_id != user.id:
        notif = Notification(
            id=generate_id(),
            user_id=l.user_id,
            type="list_like",
            title=f"{user.username} liked your list {l.title or 'Untitled'}",
            ref_id=list_id,
        )
        db.add(notif)
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


@router.post("/{list_id}/collaborators")
def add_collaborator(
    list_id: str,
    data: AddCollaborator,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    """Add a collaborator by username. Only owner can add collaborators."""
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can add collaborators")
    collaborator = db.query(User).filter(User.username == data.username.strip()).first()
    if not collaborator:
        raise HTTPException(status_code=404, detail="User not found")
    if collaborator.id == user.id:
        raise HTTPException(status_code=400, detail="You are already the owner")
    existing = db.query(ListCollaborator).filter(
        ListCollaborator.list_id == list_id,
        ListCollaborator.user_id == collaborator.id,
    ).first()
    if existing:
        return {"message": "Already a collaborator"}
    db.add(ListCollaborator(list_id=list_id, user_id=collaborator.id))
    notif = Notification(
        id=generate_id(),
        user_id=collaborator.id,
        type="collaborator_added",
        title=f"{user.username} added you as collaborator to {l.title or 'a list'}",
        ref_id=list_id,
    )
    db.add(notif)
    db.commit()
    return {"message": "ok", "user": {"id": collaborator.id, "username": collaborator.username, "avatar_url": collaborator.avatar_url}}


@router.delete("/{list_id}/collaborators/{user_id}")
def remove_collaborator(
    list_id: str,
    user_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    """Remove a collaborator. Owner can remove anyone; collaborators can remove themselves."""
    l = db.query(List).filter(List.id == list_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="List not found")
    if l.user_id == user.id:
        pass  # owner can remove anyone
    elif user_id == user.id:
        pass  # collaborator can remove self
    else:
        raise HTTPException(status_code=403, detail="Cannot remove this collaborator")
    db.query(ListCollaborator).filter(
        ListCollaborator.list_id == list_id,
        ListCollaborator.user_id == user_id,
    ).delete()
    db.commit()
    return {"message": "ok"}
