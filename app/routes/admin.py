"""Admin dashboard routes. Analytics overview of the platform."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import func
from app.config import settings
from app.database import get_db
from app.models import User, Album, Review, LogEntry, List, Follow, Track
from app.middleware.auth import get_current_user_required

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    admin_ids = {x.strip() for x in settings.admin_user_ids.split(",") if x.strip()}
    if user.id not in admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/analytics")
def get_analytics(
    user: User = Depends(get_current_user_required),
    db=Depends(get_db),
):
    """Platform analytics overview. Requires admin."""
    _require_admin(user)

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    # Core counts
    users_count = db.query(User).count()
    albums_count = db.query(Album).count()
    tracks_count = db.query(Track).count()
    reviews_count = db.query(Review).count()
    log_entries_count = db.query(LogEntry).count()
    lists_count = db.query(List).count()
    follows_count = db.query(Follow).count()

    # New users last 7 days
    new_users_7d = (
        db.query(User).filter(User.created_at >= seven_days_ago).count()
    )

    # Activity last 7 days: reviews + log entries
    reviews_7d = (
        db.query(Review).filter(Review.created_at >= seven_days_ago).count()
    )
    logs_7d = (
        db.query(LogEntry).filter(LogEntry.created_at >= seven_days_ago).count()
    )

    # Activity per day (last 14 days)
    activity_by_day = []
    for i in range(14):
        day_start = fourteen_days_ago + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        reviews_day = (
            db.query(Review)
            .filter(Review.created_at >= day_start, Review.created_at < day_end)
            .count()
        )
        logs_day = (
            db.query(LogEntry)
            .filter(LogEntry.logged_at >= day_start, LogEntry.logged_at < day_end)
            .count()
        )
        activity_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "reviews": reviews_day,
            "log_entries": logs_day,
            "total": reviews_day + logs_day,
        })

    # Top reviewers (by count)
    top_reviewers = (
        db.query(User.id, User.username, func.count(Review.id).label("cnt"))
        .join(Review, Review.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(func.count(Review.id).desc())
        .limit(10)
        .all()
    )
    top_reviewers_list = [
        {"user_id": r.id, "username": r.username, "reviews_count": r.cnt}
        for r in top_reviewers
    ]

    # Top genres (from albums)
    all_albums = db.query(Album).all()
    genre_counts = {}
    for a in all_albums:
        for g in (a.genres or []):
            if g:
                genre_counts[g] = genre_counts.get(g, 0) + 1
    top_genres = sorted(
        [{"genre": k, "count": v} for k, v in genre_counts.items()],
        key=lambda x: -x["count"],
    )[:10]

    # Recent activity (last 20 reviews)
    recent_reviews = (
        db.query(Review, User.username, Album.title, Album.artist)
        .join(User, User.id == Review.user_id)
        .join(Album, Album.id == Review.album_id)
        .order_by(Review.created_at.desc())
        .limit(20)
        .all()
    )
    recent_activity = [
        {
            "id": review.id,
            "username": username,
            "album_title": title,
            "album_artist": artist,
            "rating": review.rating,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
        for review, username, title, artist in recent_reviews
    ]

    return {
        "counts": {
            "users": users_count,
            "albums": albums_count,
            "tracks": tracks_count,
            "reviews": reviews_count,
            "log_entries": log_entries_count,
            "lists": lists_count,
            "follows": follows_count,
        },
        "last_7_days": {
            "new_users": new_users_7d,
            "reviews": reviews_7d,
            "log_entries": logs_7d,
        },
        "activity_by_day": activity_by_day,
        "top_reviewers": top_reviewers_list,
        "top_genres": top_genres,
        "recent_activity": recent_activity,
    }


@router.post("/deduplicate-albums")
def run_deduplicate_albums(user: User = Depends(get_current_user_required)):
    """Run album deduplication. Removes duplicate albums (same title, artist, year). Requires admin."""
    _require_admin(user)
    from scripts.deduplicate_albums import deduplicate_albums

    removed = deduplicate_albums()
    return {"message": "ok", "removed": removed}
