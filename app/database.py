"""Database connection and session management."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.base import Base

# Railway/Heroku use postgres:// but SQLAlchemy 1.4+ requires postgresql://
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
    poolclass=StaticPool if "sqlite" in database_url else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    if "sqlite" in database_url:
        with engine.connect() as conn:
            r = conn.execute(text("PRAGMA table_info(albums)"))
            cols = [row[1] for row in r.fetchall()]
            if "wikipedia_url" not in cols:
                conn.execute(text("ALTER TABLE albums ADD COLUMN wikipedia_url VARCHAR(512)"))
                conn.commit()
            r = conn.execute(text("PRAGMA table_info(users)"))
            cols = [row[1] for row in r.fetchall()]
            if "is_admin" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
                conn.commit()
            if "google_id" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(64)"))
                conn.commit()
            if "hashed_password" in cols:
                pass  # SQLite doesn't support ALTER COLUMN; create_all handles new schema
    else:
        # PostgreSQL: add is_admin if missing
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE NOT NULL"
                ))
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(64)"
                ))
                conn.commit()
        except Exception:
            pass  # Column may already exist from create_all
