"""
Deduplicate albums in the database by (title, artist, year).
Keeps one album per group, migrates related records to it, deletes duplicates.

Runs in parallel with seed_cron to ensure no duplicate albums remain.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import Album, Track, Review, LogEntry, ListAlbum, FavoriteAlbum


def _key(a: Album) -> tuple[str, str, int | None]:
    """Normalized key for deduplication: (title, artist, year)."""
    title = (a.title or "").strip()
    artist = (a.artist or "").strip()
    year = a.year
    return (title, artist, year)


def deduplicate_albums() -> int:
    """
    Find duplicate albums (same title, artist, year), keep one per group,
    migrate related records to the kept album, delete duplicates.
    Returns number of duplicate albums removed.
    """
    init_db()
    db = SessionLocal()

    try:
        albums = db.query(Album).all()
        groups: dict[tuple[str, str, int | None], list[Album]] = defaultdict(list)

        for a in albums:
            groups[_key(a)].append(a)

        removed = 0
        for key, group in groups.items():
            if len(group) <= 1:
                continue

            # Keep the one with cover_url, or oldest by created_at
            def _sort_key(x: Album) -> tuple:
                has_cover = 0 if x.cover_url else 1
                created = x.created_at or ""
                return (has_cover, str(created))

            group.sort(key=_sort_key, reverse=False)
            kept = group[0]
            duplicates = group[1:]

            for dup in duplicates:
                dup_id = dup.id
                kept_id = kept.id

                # Migrate Review
                db.query(Review).filter(Review.album_id == dup_id).update(
                    {Review.album_id: kept_id}
                )

                # Migrate LogEntry
                db.query(LogEntry).filter(LogEntry.album_id == dup_id).update(
                    {LogEntry.album_id: kept_id}
                )

                # Migrate ListAlbum: first remove rows that would create dup (list_id, kept_id)
                list_albums_to_update = (
                    db.query(ListAlbum)
                    .filter(ListAlbum.album_id == dup_id)
                    .all()
                )
                for la in list_albums_to_update:
                    exists_already = (
                        db.query(ListAlbum)
                        .filter(
                            ListAlbum.list_id == la.list_id,
                            ListAlbum.album_id == kept_id,
                        )
                        .first()
                    )
                    if exists_already:
                        db.delete(la)
                    else:
                        la.album_id = kept_id

                # Migrate FavoriteAlbum: delete if (user_id, kept_id) already exists
                favs_to_update = (
                    db.query(FavoriteAlbum)
                    .filter(FavoriteAlbum.album_id == dup_id)
                    .all()
                )
                for fav in favs_to_update:
                    exists_already = (
                        db.query(FavoriteAlbum)
                        .filter(
                            FavoriteAlbum.user_id == fav.user_id,
                            FavoriteAlbum.album_id == kept_id,
                        )
                        .first()
                    )
                    if exists_already:
                        db.delete(fav)
                    else:
                        fav.album_id = kept_id

                # Delete tracks and album
                db.query(Track).filter(Track.album_id == dup_id).delete()
                db.delete(dup)
                removed += 1
                print(f"  Removed duplicate: {dup.title} - {dup.artist} ({dup.year})")

        db.commit()
        return removed
    finally:
        db.close()


def main() -> None:
    print("--- Deduplicating albums ---")
    removed = deduplicate_albums()
    print(f"Deduplication complete. Removed {removed} duplicate album(s).")


if __name__ == "__main__":
    main()
