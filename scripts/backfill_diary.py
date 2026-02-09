"""
Backfill diary (LogEntry) from existing reviews.

Creates LogEntry records for reviews that don't have a matching diary entry.
Run from backend directory: python -m scripts.backfill_diary

Usage:
    python -m scripts.backfill_diary              # Backfill missing diary entries
    python -m scripts.backfill_diary --dry-run    # Preview without creating
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Review, LogEntry
from app.utils import generate_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill diary from reviews")
    parser.add_argument("--dry-run", action="store_true", help="Only preview, do not create")
    args = parser.parse_args()
    dry_run = args.dry_run

    init_db()
    db = SessionLocal()
    try:
        # Find reviews that don't have a LogEntry for same user+album
        reviews = db.query(Review).all()
        existing = set()
        for e in db.query(LogEntry).all():
            existing.add((e.user_id, e.album_id))
        to_add = [r for r in reviews if (r.user_id, r.album_id) not in existing]
        total = len(to_add)
        if total == 0:
            print("All reviews already have diary entries.")
            return
        print(f"Found {total} reviews without diary entries.")
        if dry_run:
            print("(Dry run - no changes)")
        added = 0
        for r in to_add:
            if not dry_run:
                e = LogEntry(
                    id=generate_id(),
                    user_id=r.user_id,
                    album_id=r.album_id,
                    rating=r.rating,
                    content=r.content,
                    format="digital",
                    tags=r.tags or [],
                    logged_at=r.created_at or datetime.utcnow(),
                )
                db.add(e)
                added += 1
            else:
                added += 1
        if not dry_run:
            db.commit()
        print(f"Created {added} diary entries.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
