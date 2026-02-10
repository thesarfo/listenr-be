"""
Production-quality search using PostgreSQL full-text search and trigram fuzzy matching.
Falls back to ILIKE for SQLite (local dev).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Album, User


def _is_postgres() -> bool:
    url = (settings.database_url or "").lower()
    return "postgresql" in url or "postgres" in url


def search_albums(db: Session, q: str, limit: int = 20, offset: int = 0) -> tuple[list[Album], int]:
    """
    Search albums by title and artist.
    PostgreSQL: full-text search (stemming, ranking) + trigram fuzzy (typos).
    SQLite: ILIKE substring fallback.
    Returns (albums, total_count).
    """
    q = q.strip()
    if not q:
        return [], 0

    if _is_postgres():
        return _search_albums_postgres(db, q, limit, offset)
    return _search_albums_sqlite(db, q, limit, offset)


def _search_albums_postgres(db: Session, q: str, limit: int, offset: int) -> tuple[list[Album], int]:
    """PostgreSQL: FTS + trigram similarity, ranked by relevance."""
    # plainto_tsquery: handles multi-word, stemming; "frank ocean" → frank & ocean
    # pg_trgm similarity: typo-tolerant; "fank ocian" matches "Frank Ocean"
    sql = text("""
        WITH ranked AS (
            SELECT
                a.id,
                GREATEST(
                    COALESCE(ts_rank(
                        to_tsvector('english', COALESCE(a.title, '') || ' ' || COALESCE(a.artist, '')),
                        plainto_tsquery('english', :q)
                    ), 0),
                    COALESCE(similarity(COALESCE(a.title, '') || ' ' || COALESCE(a.artist, ''), :q), 0)
                ) AS rank
            FROM albums a
            WHERE
                to_tsvector('english', COALESCE(a.title, '') || ' ' || COALESCE(a.artist, '')) @@ plainto_tsquery('english', :q)
                OR (COALESCE(a.title, '') || ' ' || COALESCE(a.artist, '')) % :q
                OR a.title ILIKE :like_q
                OR a.artist ILIKE :like_q
        )
        SELECT r.id, r.rank
        FROM ranked r
        ORDER BY r.rank DESC, r.id
        LIMIT :limit OFFSET :offset
    """)
    like_q = f"%{q}%"
    count_sql = text("""
        SELECT COUNT(*) FROM albums a
        WHERE
            to_tsvector('english', COALESCE(a.title, '') || ' ' || COALESCE(a.artist, '')) @@ plainto_tsquery('english', :q)
            OR (COALESCE(a.title, '') || ' ' || COALESCE(a.artist, '')) % :q
            OR a.title ILIKE :like_q
            OR a.artist ILIKE :like_q
    """)
    try:
        total = db.execute(count_sql, {"q": q, "like_q": like_q}).scalar() or 0
        rows = db.execute(sql, {"q": q, "like_q": like_q, "limit": limit, "offset": offset}).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return [], total
        albums = db.query(Album).filter(Album.id.in_(ids)).all()
        # Preserve rank order
        by_id = {a.id: a for a in albums}
        ordered = [by_id[i] for i in ids if i in by_id]
        return ordered, total
    except Exception:
        return _search_albums_sqlite(db, q, limit, offset)


def _search_albums_sqlite(db: Session, q: str, limit: int, offset: int) -> tuple[list[Album], int]:
    """SQLite fallback: ILIKE substring match."""
    like = f"%{q}%"
    qry = db.query(Album).filter(
        (Album.title.ilike(like)) | (Album.artist.ilike(like))
    )
    total = qry.count()
    albums = qry.offset(offset).limit(limit).all()
    return albums, total


def search_users(db: Session, q: str, limit: int = 20, offset: int = 0) -> tuple[list[User], int]:
    """
    Search users by username.
    PostgreSQL: trigram fuzzy for typo tolerance.
    SQLite: ILIKE fallback.
    """
    q = q.strip()
    if not q:
        return [], 0

    if _is_postgres():
        return _search_users_postgres(db, q, limit, offset)
    return _search_users_sqlite(db, q, limit, offset)


def _search_users_postgres(db: Session, q: str, limit: int, offset: int) -> tuple[list[User], int]:
    """PostgreSQL: trigram similarity for usernames."""
    sql = text("""
        SELECT u.id, COALESCE(similarity(u.username, :q), 0) AS rank
        FROM users u
        WHERE u.username % :q OR u.username ILIKE :like_q
        ORDER BY rank DESC, u.username
        LIMIT :limit OFFSET :offset
    """)
    like_q = f"%{q}%"
    count_sql = text("SELECT COUNT(*) FROM users u WHERE u.username % :q OR u.username ILIKE :like_q")
    try:
        total = db.execute(count_sql, {"q": q, "like_q": like_q}).scalar() or 0
        rows = db.execute(sql, {"q": q, "like_q": like_q, "limit": limit, "offset": offset}).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return [], total
        users = db.query(User).filter(User.id.in_(ids)).all()
        by_id = {u.id: u for u in users}
        ordered = [by_id[i] for i in ids if i in by_id]
        return ordered, total
    except Exception:
        return _search_users_sqlite(db, q, limit, offset)


def _search_users_sqlite(db: Session, q: str, limit: int, offset: int) -> tuple[list[User], int]:
    """SQLite fallback."""
    like = f"%{q}%"
    qry = db.query(User).filter(User.username.ilike(like))
    total = qry.count()
    users = qry.offset(offset).limit(limit).all()
    return users, total
