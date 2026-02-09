"""User routes."""
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import func
from app.database import get_db
from app.models import User, Album, Review, List, FavoriteAlbum, Follow
from app.schemas.user import UserProfileResponse, UserUpdate, FavoriteAlbumUpdate
from app.middleware.auth import get_current_user, get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/by-username/{username}")
def get_user_by_username(username: str, db=Depends(get_db)):
    """Public profile by username (for shareable links)."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return get_user(user.id, db)


@router.get("/recommended")
def get_recommended(
    db=Depends(get_db),
    limit: int = 10,
    current_user: User | None = Depends(get_current_user),
):
    qry = db.query(User)
    if current_user:
        qry = qry.filter(User.id != current_user.id)
    users = qry.limit(limit).all()
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in users]


@router.get("/{user_id}")
def get_user(user_id: str, db=Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    albums = db.query(func.count(Review.id)).filter(Review.user_id == user_id).scalar() or 0
    reviews = db.query(func.count(Review.id)).filter(Review.user_id == user_id).scalar() or 0
    lists = db.query(func.count(List.id)).filter(List.user_id == user_id).scalar() or 0
    following_count = db.query(func.count(Follow.following_id)).filter(Follow.follower_id == user_id).scalar() or 0
    followers_count = db.query(func.count(Follow.follower_id)).filter(Follow.following_id == user_id).scalar() or 0
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "created_at": user.created_at.isoformat(),
        "albums_count": albums,
        "reviews_count": reviews,
        "lists_count": lists,
        "following_count": following_count,
        "followers_count": followers_count,
    }


@router.get("/{user_id}/diary")
def get_user_diary(
    user_id: str,
    db=Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    """Get a user's diary (log entries). Public endpoint for profile viewing."""
    from app.models import LogEntry
    qry = db.query(LogEntry).filter(LogEntry.user_id == user_id)
    total = qry.count()
    entries = qry.order_by(LogEntry.logged_at.desc()).offset(offset).limit(limit).all()
    result = []
    for e in entries:
        a = db.query(Album).filter(Album.id == e.album_id).first()
        result.append({
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
        })
    return {"data": result, "total": total, "limit": limit, "offset": offset}


@router.get("/{user_id}/reviews")
def get_user_reviews(
    user_id: str,
    db=Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    from app.models import Review, Like, Comment
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
    qry = db.query(Review).filter(Review.user_id == user_id)
    total = qry.count()
    reviews = qry.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
    return {"data": [_to_dict(r) for r in reviews], "total": total, "limit": limit, "offset": offset}


@router.get("/{user_id}/lists")
def get_user_lists(
    user_id: str,
    db=Depends(get_db),
):
    from app.models import List, ListAlbum, ListLike
    lists = db.query(List).filter(List.user_id == user_id).all()
    result = []
    for l in lists:
        albums_count = db.query(func.count(ListAlbum.id)).filter(ListAlbum.list_id == l.id).scalar() or 0
        likes = db.query(func.count(ListLike.user_id)).filter(ListLike.list_id == l.id).scalar() or 0
        result.append({
            "id": l.id, "user_id": l.user_id, "title": l.title,
            "description": l.description, "cover_url": l.cover_url,
            "albums_count": albums_count, "likes": likes,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })
    return result


@router.get("/{user_id}/favorites")
def get_favorites(user_id: str, db=Depends(get_db)):
    favs = (
        db.query(FavoriteAlbum, Album)
        .join(Album, FavoriteAlbum.album_id == Album.id)
        .filter(FavoriteAlbum.user_id == user_id)
        .order_by(FavoriteAlbum.position)
        .all()
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "artist": a.artist,
            "year": a.year,
            "cover_url": a.cover_url,
            "genres": a.genres or [],
        }
        for _, a in favs
    ]


@router.put("/me")
def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.bio is not None:
        user.bio = data.bio
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "avatar_url": user.avatar_url, "bio": user.bio}


@router.put("/me/favorites")
def update_favorites(
    data: FavoriteAlbumUpdate,
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    db.query(FavoriteAlbum).filter(FavoriteAlbum.user_id == user.id).delete()
    for i, aid in enumerate(data.album_ids):
        fav = FavoriteAlbum(user_id=user.id, album_id=aid, position=i)
        db.add(fav)
    db.commit()
    return {"message": "ok"}


@router.post("/{user_id}/follow")
def follow_user(
    user_id: str,
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot follow self")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Follow).filter(
        Follow.follower_id == user.id, Follow.following_id == user_id
    ).first()
    if existing:
        return {"message": "Already following"}
    f = Follow(follower_id=user.id, following_id=user_id)
    db.add(f)
    db.commit()
    return {"message": "ok"}


@router.delete("/{user_id}/follow")
def unfollow_user(
    user_id: str,
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    db.query(Follow).filter(
        Follow.follower_id == user.id, Follow.following_id == user_id
    ).delete()
    db.commit()
    return {"message": "ok"}


@router.get("/me/following")
def get_following(
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    follows = (
        db.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == user.id)
        .all()
    )
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in follows]
