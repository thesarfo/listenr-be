"""Review routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import func
from app.database import get_db
from app.models import Review, LogEntry, Like, Comment, Album, User, Follow
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse, CommentCreate
from app.middleware.auth import get_current_user_required, get_current_user
from app.utils import generate_id

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _review_to_dict(r: Review, db, include_user=True, include_album=True):
    likes = db.query(func.count(Like.user_id)).filter(Like.review_id == r.id).scalar() or 0
    comments = db.query(func.count(Comment.id)).filter(Comment.review_id == r.id).scalar() or 0
    d = {
        "id": r.id,
        "user_id": r.user_id,
        "album_id": r.album_id,
        "rating": r.rating,
        "content": r.content,
        "type": r.type,
        "tags": r.tags or [],
        "share_to_feed": r.share_to_feed,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "likes": likes,
        "comments": comments,
    }
    if include_user:
        u = db.query(User).filter(User.id == r.user_id).first()
        d["user_name"] = u.username if u else None
        d["user_avatar"] = u.avatar_url if u else None
    if include_album:
        a = db.query(Album).filter(Album.id == r.album_id).first()
        d["album_title"] = a.title if a else None
        d["album_cover"] = a.cover_url if a else None
    return d


@router.post("")
def create_review(
    data: ReviewCreate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    r = Review(
        id=generate_id(),
        user_id=user.id,
        album_id=data.album_id,
        rating=data.rating,
        content=data.content,
        type=data.type,
        tags=data.tags,
        share_to_feed=data.share_to_feed,
    )
    db.add(r)
    db.flush()
    # Also create diary entry so logging an album always appears in the diary
    e = LogEntry(
        id=generate_id(),
        user_id=user.id,
        album_id=data.album_id,
        rating=data.rating,
        content=data.content,
        format="digital",
        tags=data.tags or [],
        logged_at=datetime.utcnow(),
    )
    db.add(e)
    db.commit()
    db.refresh(r)
    return _review_to_dict(r, db)


@router.get("")
def get_feed(
    user=Depends(get_current_user_required),
    db=Depends(get_db),
    filter: str = Query("all", description="all|reviews"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    following = db.query(Follow.following_id).filter(Follow.follower_id == user.id).subquery()
    qry = db.query(Review).filter(
        Review.user_id.in_(following),
        Review.share_to_feed == True,
    )
    if filter == "reviews":
        qry = qry.filter(Review.type == "review")
    total = qry.count()
    reviews = qry.order_by(Review.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "data": [_review_to_dict(r, db) for r in reviews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{review_id}")
def get_review(review_id: str, db=Depends(get_db)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return _review_to_dict(r, db)


@router.patch("/{review_id}")
def update_review(
    review_id: str,
    data: ReviewUpdate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your review")
    if data.rating is not None:
        r.rating = data.rating
    if data.content is not None:
        r.content = data.content
    if data.tags is not None:
        r.tags = data.tags
    if data.share_to_feed is not None:
        r.share_to_feed = data.share_to_feed
    db.commit()
    db.refresh(r)
    return _review_to_dict(r, db)


@router.delete("/{review_id}")
def delete_review(
    review_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your review")
    db.delete(r)
    db.commit()
    return {"message": "ok"}


@router.post("/{review_id}/like")
def like_review(
    review_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    existing = db.query(Like).filter(Like.user_id == user.id, Like.review_id == review_id).first()
    if existing:
        return {"message": "Already liked"}
    like = Like(user_id=user.id, review_id=review_id)
    db.add(like)
    db.commit()
    return {"message": "ok"}


@router.delete("/{review_id}/like")
def unlike_review(
    review_id: str,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    db.query(Like).filter(Like.user_id == user.id, Like.review_id == review_id).delete()
    db.commit()
    return {"message": "ok"}


@router.get("/{review_id}/comments")
def get_comments(
    review_id: str,
    db=Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    comments = (
        db.query(Comment)
        .filter(Comment.review_id == review_id)
        .order_by(Comment.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(Comment).filter(Comment.review_id == review_id).count()
    return {
        "data": [
            {
                "id": c.id,
                "user_id": c.user_id,
                "review_id": c.review_id,
                "content": c.content,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{review_id}/comments")
def add_comment(
    review_id: str,
    data: CommentCreate,
    user=Depends(get_current_user_required),
    db=Depends(get_db),
):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    c = Comment(
        id=generate_id(),
        user_id=user.id,
        review_id=review_id,
        content=data.content,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {
        "id": c.id,
        "user_id": c.user_id,
        "review_id": c.review_id,
        "content": c.content,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
