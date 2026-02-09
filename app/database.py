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
    # SQLite-only migration: add wikipedia_url column if missing
    if "sqlite" in database_url:
        with engine.connect() as conn:
            r = conn.execute(text("PRAGMA table_info(albums)"))
            cols = [row[1] for row in r.fetchall()]
            if "wikipedia_url" not in cols:
                conn.execute(text("ALTER TABLE albums ADD COLUMN wikipedia_url VARCHAR(512)"))
                conn.commit()
