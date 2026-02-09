"""
Seed albums from Spotify API.

Uses Client Credentials flow. Fetches albums via New Releases or Search,
then fetches full album details (including tracks) via Get Album.

Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env or environment.

Usage (run from backend/ directory):
    python scripts/seed_albums_spotify.py                    # Seed 50 albums from new releases
    python scripts/seed_albums_spotify.py --count 100        # Seed 100 albums
    python scripts/seed_albums_spotify.py --query "rock"     # Search for "rock" albums
    python scripts/seed_albums_spotify.py --query "year:2024"  # Albums from 2024
    python scripts/seed_albums_spotify.py --clear            # Clear existing albums before seeding

For Railway/cron/containers, use the file path form above (not python -m).
"""
import argparse
import base64
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Album, Track
from app.utils import generate_id


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
RATE_LIMIT_DELAY = 0.2  # seconds between API calls


def get_access_token() -> str:
    """Get Spotify access token via Client Credentials flow."""
    client_id = settings.spotify_client_id or ""
    client_secret = settings.spotify_client_secret or ""
    if not client_id or not client_secret:
        raise RuntimeError("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env")
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = httpx.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def _get(url: str, token: str, **kwargs) -> dict | None:
    """GET with auth, return JSON or None."""
    headers = {"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = httpx.get(url, headers=headers, timeout=15, **kwargs)
        if resp.status_code == 200:
            return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout, Exception):
        pass
    return None


def fetch_new_releases(token: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Get new album releases. Returns list of simplified album objects."""
    url = f"{SPOTIFY_API_BASE}/browse/new-releases"
    data = _get(url, token, params={"limit": min(limit, 50), "offset": offset})
    if not data or "albums" not in data:
        return []
    return data["albums"].get("items", [])


def search_albums(token: str, query: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Search for albums. Returns list of simplified album objects."""
    url = f"{SPOTIFY_API_BASE}/search"
    data = _get(url, token, params={"q": query, "type": "album", "limit": min(limit, 50), "offset": offset})
    if not data or "albums" not in data:
        return []
    return data["albums"].get("items", [])


def fetch_album(token: str, album_id: str) -> dict | None:
    """Get full album details including tracks. https://developer.spotify.com/documentation/web-api/reference/get-an-album"""
    url = f"{SPOTIFY_API_BASE}/albums/{album_id}"
    return _get(url, token, params={"market": "US"})


def parse_year(date_str: str | None) -> int | None:
    """Extract year from release_date (YYYY, YYYY-MM-DD, etc)."""
    if not date_str:
        return None
    m = re.match(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def ms_to_duration(ms: int | None) -> str | None:
    """Convert milliseconds to 'M:SS' format."""
    if ms is None or ms <= 0:
        return None
    m, s = divmod(ms // 1000, 60)
    return f"{m}:{s:02d}"


def seed(
    count: int = 50,
    clear: bool = False,
    query: str | None = None,
) -> None:
    """Seed albums from Spotify."""
    init_db()
    token = get_access_token()

    db = SessionLocal()
    try:
        if clear:
            db.query(Track).delete()
            db.query(Album).delete()
            db.commit()
            print("Cleared existing albums and tracks.")

        existing = {(a.title, a.artist, a.year) for a in db.query(Album).all()}
        existing_spotify_ids = {a.spotify_id for a in db.query(Album).filter(Album.spotify_id.isnot(None)).all()}
        seeded = 0
        offset = 0
        batch_size = 50

        while seeded < count:
            if query:
                albums_batch = search_albums(token, query, limit=batch_size, offset=offset)
            else:
                albums_batch = fetch_new_releases(token, limit=batch_size, offset=offset)

            if not albums_batch:
                print("No more albums.")
                break

            for item in albums_batch:
                if seeded >= count:
                    break

                album_id = item.get("id")
                if not album_id or album_id in existing_spotify_ids:
                    continue

                title = (item.get("name") or "").strip() or "Unknown"
                artists = item.get("artists") or []
                artist = artists[0].get("name", "Unknown") if artists else "Unknown"
                year = parse_year(item.get("release_date"))
                cover_url = None
                if item.get("images"):
                    cover_url = item["images"][0].get("url")

                if (title, artist, year) in existing:
                    print(f"  Skip duplicate: {title} - {artist}")
                    continue

                if item.get("album_type") == "single" and count > 20:
                    continue  # Prefer full albums when seeding many

                print(f"  Fetching: {title} - {artist} ({album_id})")

                full = fetch_album(token, album_id)
                if not full:
                    print("    Failed to get album detail")
                    continue

                tracks_data = full.get("tracks", {})
                track_items = tracks_data.get("items", [])
                total_tracks = tracks_data.get("total", 0)

                # Paginate tracks if needed (Spotify returns max 50 per request)
                while len(track_items) < total_tracks and tracks_data.get("next"):
                    time.sleep(RATE_LIMIT_DELAY)
                    resp = httpx.get(
                        tracks_data["next"],
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        tracks_data = resp.json()
                        track_items.extend(tracks_data.get("items", []))

                if not track_items:
                    print("    No tracks, skipping")
                    continue

                cover_url = cover_url or (full.get("images") or [{}])[0].get("url")
                label = full.get("label")
                total_duration_ms = sum(t.get("duration_ms") or 0 for t in track_items)
                length_seconds = total_duration_ms // 1000 if total_duration_ms else None

                album = Album(
                    id=generate_id(),
                    title=title,
                    artist=artist,
                    year=year,
                    cover_url=cover_url,
                    genres=[],
                    label=label,
                    length_seconds=length_seconds,
                    spotify_id=album_id,
                )
                db.add(album)
                db.flush()

                track_num = 1
                for t in track_items:
                    dur_ms = t.get("duration_ms")
                    track = Track(
                        id=generate_id(),
                        album_id=album.id,
                        number=track_num,
                        title=(t.get("name") or "Unknown").strip() or "Unknown",
                        duration=ms_to_duration(dur_ms),
                    )
                    db.add(track)
                    track_num += 1

                existing.add((title, artist, year))
                existing_spotify_ids.add(album_id)
                seeded += 1
                print(f"    Seeded ({seeded}/{count})")

            offset += len(albums_batch)
            db.commit()
            print(f"Committed. Total seeded: {seeded}")

        print(f"Done. Seeded {seeded} albums from Spotify.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed albums from Spotify API",
        epilog="Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env",
    )
    parser.add_argument("--count", "-n", type=int, default=50, help="Total albums to seed")
    parser.add_argument("--clear", action="store_true", help="Clear existing albums before seeding")
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Search query (e.g. 'rock', 'year:2024', 'artist:Taylor Swift'). If omitted, uses New Releases.",
    )
    args = parser.parse_args()
    seed(count=args.count, clear=args.clear, query=args.query)


if __name__ == "__main__":
    main()
