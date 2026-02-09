"""
Backfill album descriptions for albums that have none.

Fetches from Wikipedia (first paragraph of album article).
Run from backend directory: python -m scripts.backfill_descriptions

Usage:
    python -m scripts.backfill_descriptions              # Backfill all albums with null description
    python -m scripts.backfill_descriptions --dry-run    # Preview without updating DB
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Album
from app.services.album_description import fetch_description_for_album


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill album descriptions")
    parser.add_argument("--dry-run", action="store_true", help="Only preview, do not update DB")
    args = parser.parse_args()
    dry_run = args.dry_run

    init_db()
    db = SessionLocal()
    try:
        albums = db.query(Album).filter(
            (Album.description.is_(None)) | (Album.description == "")
        ).all()
        total = len(albums)
        if total == 0:
            print("No albums with missing descriptions.")
            return
        print(f"Found {total} albums with missing descriptions.")
        if dry_run:
            print("(Dry run - no DB updates)")
        updated = 0
        for i, a in enumerate(albums):
            print(f"  [{i + 1}/{total}] {a.title} - {a.artist}...", end=" ", flush=True)
            desc, wiki_url = fetch_description_for_album(a.title, a.artist, release_group_mbid=None)
            if desc:
                if not dry_run:
                    a.description = desc
                    if wiki_url:
                        a.wikipedia_url = wiki_url
                    db.commit()
                print(f"OK ({len(desc)} chars)")
                updated += 1
            else:
                print("not found")
        print(f"\nDone. Updated {updated}/{total} descriptions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
