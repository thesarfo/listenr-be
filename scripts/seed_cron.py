"""
Cron-friendly album seeding: reads priority batches from seed_priorities.txt,
then seeds albums for each (genre, country, artist, count) batch.
Runs deduplication in parallel to remove duplicate albums.

For Railway cron: set start command to:
  python -m scripts.seed_cron

Suggested schedule: 0 2 * * * (daily at 2am UTC)

Text file format (seed_priorities.txt):
  genre, country, artist, count
  Empty or - means "any". Lines starting with # are ignored.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_albums import seed
from scripts.deduplicate_albums import deduplicate_albums

PRIORITIES_FILE = Path(__file__).resolve().parent / "seed_priorities.txt"


def _parse_line(line: str) -> tuple[str | None, str | None, str | None, int] | None:
    """Parse a line into (genre, country, artist, count). Returns None for skip."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split(",", 3)]
    if len(parts) < 4:
        return None
    genre = parts[0] or None
    country = parts[1] or None
    artist = parts[2] or None
    if genre == "-":
        genre = None
    if country == "-":
        country = None
    if artist == "-":
        artist = None
    try:
        count = int(parts[3].strip())
    except (ValueError, IndexError):
        return None
    if count <= 0:
        return None
    return genre, country, artist, count


def load_priorities(path: Path) -> list[tuple[str | None, str | None, str | None, int]]:
    """Load priority batches from text file."""
    if not path.exists():
        print(f"Warning: {path} not found, using default batches.")
        return [
            ("hip hop", "US", None, 10),
            ("hip hop", "GH", None, 10),
            (None, None, None, 15),
        ]
    batches: list[tuple[str | None, str | None, str | None, int]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if parsed:
                batches.append(parsed)
    return batches


def main() -> None:
    batches = load_priorities(PRIORITIES_FILE)
    total_target = 0

    # Run deduplication in parallel with seeding
    def run_dedup() -> None:
        try:
            deduplicate_albums()
        except Exception as e:
            print(f"Deduplication error: {e}")

    dedup_thread = threading.Thread(target=run_dedup, daemon=True)
    dedup_thread.start()

    for genre, country, artist, count in batches:
        filter_parts = []
        if genre:
            filter_parts.append(f"genre={genre}")
        if country:
            filter_parts.append(f"country={country}")
        if artist:
            filter_parts.append(f"artist={artist}")
        filter_str = ", ".join(filter_parts) if filter_parts else "general"
        print(f"\n--- Seeding {filter_str} (up to {count} albums) ---")
        seed(count=count, batch_size=25, genre=genre, country=country, artist=artist)
        total_target += count

    dedup_thread.join(timeout=300)  # Wait up to 5 min for dedup to finish

    print(f"\nCron seed complete. Target: {total_target} albums (duplicates skipped).")


if __name__ == "__main__":
    main()
