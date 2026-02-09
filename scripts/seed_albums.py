"""
Seed albums and tracks from MusicBrainz API.

Fetches albums in batches of 100, maps to Album/Track schema, and seeds the database.
Uses MusicBrainz (releases + recordings) and Cover Art Archive for cover images.

Usage:
    python -m scripts.seed_albums                    # Seed 100 albums (default)
    python -m scripts.seed_albums --count 200        # Seed 200 albums
    python -m scripts.seed_albums --batch 50         # Fetch 50 per API batch
    python -m scripts.seed_albums --clear            # Clear existing albums before seeding
    python -m scripts.seed_albums --genre jazz       # Filter by genre (MusicBrainz tag)
    python -m scripts.seed_albums --country US       # Filter by country (ISO 3166-1 alpha-2)
    python -m scripts.seed_albums -g rock -c GB      # Combine genre + country
    python -m scripts.seed_albums --artist "The Beatles"  # Filter by artist name
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.database import SessionLocal, init_db
from app.models import Album, Track
from app.services.cover_art import fetch_cover_for_album
from app.services.album_description import fetch_description_for_album
from app.utils import generate_id


# MusicBrainz requires a descriptive User-Agent
USER_AGENT = "Listenr/1.0 (https://github.com/musicboxd)"
MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
RATE_LIMIT_DELAY = 1.1  # seconds between requests (MusicBrainz asks for max 1/sec)
MAX_RETRIES = 5
RETRY_BASE_DELAY = 5  # seconds, doubles on each retry


def _http_get(url: str, **kwargs) -> httpx.Response:
    """GET with retries for transient connection errors."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            return httpx.get(url, **kwargs)
        except (httpx.ConnectError, httpx.ReadTimeout, ConnectionError, OSError) as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                print(f"    Connection error, retry in {delay}s... ({attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                raise last_err
    raise last_err or RuntimeError("Unexpected retry loop exit")


def ms_to_duration(ms: int | None) -> str | None:
    """Convert milliseconds to 'M:SS' format."""
    if ms is None or ms <= 0:
        return None
    m, s = divmod(ms // 1000, 60)
    return f"{m}:{s:02d}"


def parse_year(date_str: str | None) -> int | None:
    """Extract year from MusicBrainz date (YYYY, YYYY-MM-DD, etc)."""
    if not date_str:
        return None
    m = re.match(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def build_search_query(
    genre: str | None = None,
    country: str | None = None,
    artist: str | None = None,
) -> str:
    """Build Lucene-style search query for releases."""
    parts = ["status:official", "primarytype:album"]
    if genre:
        parts.append(f"tag:{genre.strip()}")
    if country:
        code = country.strip().upper()[:2]
        if len(code) == 2:
            parts.append(f"country:{code}")
    if artist:
        name = artist.strip()
        if " " in name:
            parts.append(f'artist:"{name}"')
        else:
            parts.append(f"artist:{name}")
    return " ".join(parts)


def fetch_releases(
    offset: int,
    limit: int,
    genre: str | None = None,
    country: str | None = None,
    artist: str | None = None,
) -> list[dict]:
    """Search MusicBrainz for official albums, optionally by genre, country, and/or artist."""
    url = f"{MB_BASE}/release"
    query = build_search_query(genre=genre, country=country, artist=artist)
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "fmt": "json",
    }
    headers = {"User-Agent": USER_AGENT}
    resp = _http_get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("releases", [])


def fetch_release_detail(mbid: str) -> dict | None:
    """Fetch release with recordings (tracks) and artist credits."""
    url = f"{MB_BASE}/release/{mbid}"
    params = {"inc": "recordings+artists", "fmt": "json"}
    headers = {"User-Agent": USER_AGENT}
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = _http_get(url, params=params, headers=headers, timeout=30)
    except (httpx.ConnectError, httpx.ReadTimeout, ConnectionError, OSError):
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def fetch_release_group_genres(rgid: str) -> list[str]:
    """Fetch top genre names for a release-group."""
    if not rgid:
        return []
    url = f"{MB_BASE}/release-group/{rgid}"
    params = {"inc": "genres", "fmt": "json"}
    headers = {"User-Agent": USER_AGENT}
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = _http_get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        genres = data.get("genres", [])
        return [g.get("name", "") for g in genres if g.get("name")][:5]
    except (httpx.ConnectError, httpx.ReadTimeout, Exception):
        return []


def fetch_cover_url(mbid: str) -> str | None:
    """Fetch front cover URL from Cover Art Archive."""
    url = f"{CAA_BASE}/release/{mbid}"
    headers = {"User-Agent": USER_AGENT}
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = _http_get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        images = data.get("images", [])
        for img in images:
            if img.get("front"):
                return img.get("image") or (img.get("thumbnails", {}).get("500"))
        if images:
            return images[0].get("image") or (images[0].get("thumbnails", {}).get("500"))
    except (httpx.ConnectError, httpx.ReadTimeout, Exception):
        pass
    return None


def release_to_album_and_tracks(
    release: dict,
    cover_url: str | None,
    genres: list[str] | None = None,
    description: str | None = None,
    wikipedia_url: str | None = None,
) -> tuple[dict, list[dict]]:
    """Map MusicBrainz release to Album dict and list of Track dicts."""
    title = release.get("title") or "Unknown"
    artist = "Unknown"
    if release.get("artist-credit"):
        artist = release["artist-credit"][0].get("name", "Unknown")

    year = parse_year(release.get("date"))
    label = None
    if release.get("label-info") and release["label-info"]:
        label = release["label-info"][0].get("label", {}).get("name")

    # Collect tracks from all media (discs)
    tracks_data: list[dict] = []
    track_num = 1
    total_length_ms = 0

    for medium in release.get("media", []):
        for t in medium.get("tracks", []):
            length_ms = t.get("length") or t.get("recording", {}).get("length")
            duration = ms_to_duration(length_ms)
            if length_ms:
                total_length_ms += length_ms

            tracks_data.append({
                "number": track_num,
                "title": t.get("title") or "Unknown",
                "duration": duration,
            })
            track_num += 1

    length_seconds = total_length_ms // 1000 if total_length_ms else None

    album_data = {
        "title": title,
        "artist": artist,
        "year": year,
        "cover_url": cover_url,
        "genres": genres or [],
        "label": label,
        "length_seconds": length_seconds,
        "description": description,
        "wikipedia_url": wikipedia_url,
    }
    return album_data, tracks_data


def seed(
    count: int = 100,
    batch_size: int = 100,
    clear: bool = False,
    genre: str | None = None,
    country: str | None = None,
    artist: str | None = None,
) -> None:
    """Seed albums and tracks from MusicBrainz."""
    init_db()
    db = SessionLocal()

    try:
        if clear:
            deleted_tracks = db.query(Track).delete()
            deleted_albums = db.query(Album).delete()
            db.commit()
            print(f"Cleared {deleted_albums} albums and {deleted_tracks} tracks.")

        existing = {(a.title, a.artist, a.year) for a in db.query(Album).all()}
        seeded = 0
        offset = 0

        filter_desc = []
        if genre:
            filter_desc.append(f"genre={genre}")
        if country:
            filter_desc.append(f"country={country.upper()[:2]}")
        if artist:
            filter_desc.append(f"artist={artist}")
        filter_str = f" [{', '.join(filter_desc)}]" if filter_desc else ""

        while seeded < count:
            print(f"Fetching releases (offset={offset}, limit={batch_size}){filter_str}...")
            releases = fetch_releases(offset, batch_size, genre=genre, country=country, artist=artist)
            if not releases:
                print("No more releases.")
                break

            for rel in releases:
                if seeded >= count:
                    break

                title = rel.get("title") or "Unknown"
                artist = "Unknown"
                if rel.get("artist-credit"):
                    artist = rel["artist-credit"][0].get("name", "Unknown")
                year = parse_year(rel.get("date"))

                if (title, artist, year) in existing:
                    print(f"  Skip duplicate: {title} - {artist}")
                    continue

                mbid = rel.get("id")
                if not mbid:
                    continue

                print(f"  Fetching: {title} - {artist} ({mbid})")

                detail = fetch_release_detail(mbid)
                if not detail:
                    print(f"    Failed to get release detail")
                    continue

                cover_url = fetch_cover_url(mbid)
                if not cover_url:
                    cover_url = fetch_cover_for_album(title, artist)

                genres_list: list[str] = []
                rgid = detail.get("release-group", {}).get("id") or rel.get("release-group", {}).get("id")
                if rgid:
                    genres_list = fetch_release_group_genres(rgid)

                description, wikipedia_url = fetch_description_for_album(title, artist, rgid)

                album_data, tracks_data = release_to_album_and_tracks(
                    detail, cover_url, genres=genres_list, description=description, wikipedia_url=wikipedia_url
                )

                if not tracks_data:
                    print(f"    No tracks, skipping")
                    continue

                album = Album(
                    id=generate_id(),
                    title=album_data["title"],
                    artist=album_data["artist"],
                    year=album_data["year"],
                    cover_url=album_data["cover_url"],
                    genres=album_data["genres"],
                    label=album_data["label"],
                    length_seconds=album_data["length_seconds"],
                    description=album_data["description"],
                    wikipedia_url=album_data.get("wikipedia_url"),
                )
                db.add(album)
                db.flush()

                for t in tracks_data:
                    track = Track(
                        id=generate_id(),
                        album_id=album.id,
                        number=t["number"],
                        title=t["title"],
                        duration=t["duration"],
                    )
                    db.add(track)

                existing.add((title, artist, year))
                seeded += 1
                print(f"    Seeded ({seeded}/{count})")

            offset += len(releases)
            db.commit()
            print(f"Committed batch. Total seeded: {seeded}")

        print(f"Done. Seeded {seeded} albums with tracks.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed albums and tracks from MusicBrainz",
        epilog="Examples: --genre jazz  --country US  --artist \"The Beatles\"",
    )
    parser.add_argument("--count", "-n", type=int, default=100, help="Total albums to seed")
    parser.add_argument("--batch", "-b", type=int, default=100, help="Albums per API batch")
    parser.add_argument("--clear", action="store_true", help="Clear existing albums before seeding")
    parser.add_argument(
        "--genre", "-g",
        type=str,
        default=None,
        help="Filter by genre (MusicBrainz tag, e.g. jazz, rock, hip hop)",
    )
    parser.add_argument(
        "--country", "-c",
        type=str,
        default=None,
        help="Filter by country (ISO 3166-1 alpha-2, e.g. US, GB, JP, DE)",
    )
    parser.add_argument(
        "--artist", "-a",
        type=str,
        default=None,
        help="Filter by artist name (e.g. 'The Beatles', 'Taylor Swift')",
    )
    args = parser.parse_args()
    seed(
        count=args.count,
        batch_size=args.batch,
        clear=args.clear,
        genre=args.genre,
        country=args.country,
        artist=args.artist,
    )


if __name__ == "__main__":
    main()
