"""
Backfill album cover images for albums that have none.

Fetches official covers from MusicBrainz/Cover Art Archive and iTunes.
Run from backend directory: python -m scripts.backfill_covers

Usage:
    python -m scripts.backfill_covers              # Backfill all albums with null cover
    python -m scripts.backfill_covers --dry-run    # Preview without updating DB
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Album
from app.services.cover_art import fetch_cover_for_album


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill album cover images")
    parser.add_argument("--dry-run", action="store_true", help="Only preview, do not update DB")
    args = parser.parse_args()
    dry_run = args.dry_run

    init_db()
    db = SessionLocal()
    try:
        albums = db.query(Album).filter(
            (Album.cover_url.is_(None)) | (Album.cover_url == "")
        ).all()
        total = len(albums)
        if total == 0:
            print("No albums with missing covers.")
            return
        print(f"Found {total} albums with missing covers.")
        if dry_run:
            print("(Dry run - no DB updates)")
        updated = 0
        for i, a in enumerate(albums):
            print(f"  [{i + 1}/{total}] {a.title} - {a.artist}...", end=" ", flush=True)
            url = fetch_cover_for_album(a.title, a.artist, a.year)
            if url:
                if not dry_run:
                    a.cover_url = url
                    db.commit()
                print(f"OK ({url[:60]}...)")
                updated += 1
            else:
                print("not found")
        print(f"\nDone. Updated {updated}/{total} covers.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
