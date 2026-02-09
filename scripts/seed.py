"""Seed script to populate initial data for development."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import User, Album, Track
from app.services.auth import get_password_hash
from app.utils import generate_id

def seed():
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).first():
            print("Database already seeded.")
            return
        user = User(
            id=generate_id(),
            username="music_connoisseur",
            email="demo@musicboxd.com",
            hashed_password=get_password_hash("demo123"),
            bio="Dedicated crate digger. Exploring Japanese jazz fusion, 70s soul, and early synth-pop.",
        )
        db.add(user)
        albums = [
            ("Currents", "Tame Impala", 2015, ["Psychedelic Pop", "Electronic"]),
            ("To Pimp A Butterfly", "Kendrick Lamar", 2015, ["Conscious Hip Hop", "Jazz Rap", "Funk"]),
            ("The New Abnormal", "The Strokes", 2020, ["Indie Rock"]),
        ]
        for title, artist, year, genres in albums:
            a = Album(
                id=generate_id(),
                title=title,
                artist=artist,
                year=year,
                cover_url=None,  # Use seed_albums.py for real covers from Cover Art Archive
                genres=genres,
            )
            db.add(a)
        db.commit()
        print("Seed complete. User: demo@musicboxd.com / demo123")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
