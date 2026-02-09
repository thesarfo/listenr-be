"""
Cron-friendly album seeding: prioritizes hip hop/rap from US and Ghana, then other genres.

For Railway cron: set start command to:
  python -m scripts.seed_cron

Suggested schedule: 0 2 * * * (daily at 2am UTC)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_albums import seed

# Priority batches: (genre, country, count)
PRIORITY_BATCHES = [
    ("hip hop", "US", 10),
    ("hip hop", "GH", 10),
    ("rap", "US", 10),
    ("rap", "GH", 10),
]

# Fallback: general albums (no filter)
GENERAL_COUNT = 10


def main() -> None:
    total = 0
    for genre, country, count in PRIORITY_BATCHES:
        print(f"\n--- Seeding {genre} from {country} (up to {count} albums) ---")
        seed(count=count, batch_size=25, genre=genre, country=country)
        total += count

    print(f"\n--- Seeding general albums (up to {GENERAL_COUNT}) ---")
    seed(count=GENERAL_COUNT, batch_size=25)
    total += GENERAL_COUNT

    print(f"\nCron seed complete. Target: {total} albums (duplicates skipped).")


if __name__ == "__main__":
    main()
