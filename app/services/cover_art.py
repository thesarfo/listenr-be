"""
Fetch official album cover art from multiple sources.

Sources (in order): DodoApps Artwork API, iTunes, Cover Art Archive.
All are free and require no API keys.
"""
import time
import urllib.parse
from typing import Optional

import httpx

USER_AGENT = "Listenr/1.0 (https://github.com/listenr)"
DODO_ARTWORK_URL = "https://artwork.dodoapps.io/"
MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
ITUNES_BASE = "https://itunes.apple.com/search"


def _get(url: str, **kwargs) -> Optional[dict]:
    """GET with User-Agent, return JSON or None."""
    headers = kwargs.pop("headers", {})
    headers["User-Agent"] = USER_AGENT
    try:
        resp = httpx.get(url, headers=headers, timeout=15, **kwargs)
        if resp.status_code == 200:
            return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout, Exception):
        pass
    return None


def _post(url: str, json: dict, **kwargs) -> Optional[dict]:
    """POST with JSON body, return parsed JSON or None."""
    headers = kwargs.pop("headers", {})
    headers["User-Agent"] = USER_AGENT
    headers.setdefault("Content-Type", "application/json")
    try:
        resp = httpx.post(url, json=json, headers=headers, timeout=15, **kwargs)
        if resp.status_code == 200:
            return resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout, Exception):
        pass
    return None


def fetch_from_dodo_artwork(title: str, artist: str) -> Optional[str]:
    """
    Fetch artwork from DodoApps Artwork API.
    POST with search query, returns 600x600 thumb or large cover URL.
    """
    search = f"{title} {artist}".strip()
    if not search:
        return None
    data = _post(DODO_ARTWORK_URL, {"search": search, "storefront": "us", "type": "album"})
    if not data or not data.get("images"):
        return None
    title_lower = title.lower()
    artist_lower = artist.lower()
    for img in data["images"]:
        img_name = (img.get("name") or "").lower()
        img_artist = (img.get("artist") or "").lower()
        if title_lower in img_name or img_name in title_lower:
            if artist_lower in img_artist or img_artist in artist_lower:
                return img.get("large") or img.get("thumb")
    return data["images"][0].get("large") or data["images"][0].get("thumb")


def _itunes_artwork_url(artwork_url_100: str, size: int = 500) -> str:
    """Upgrade iTunes artwork URL to higher resolution (up to 600x600)."""
    if not artwork_url_100:
        return ""
    # iTunes URLs: .../source/100x100bb.jpg or .../100x100-75.png
    for old in ("100x100bb", "100x100-75", "100x100", "60x60bb", "60x60"):
        if old in artwork_url_100:
            suffix = "bb" if "bb" in old or "75" in old else ""
            return artwork_url_100.replace(old, f"{size}x{size}{suffix}")
    return artwork_url_100


def fetch_from_cover_art_archive(title: str, artist: str) -> Optional[str]:
    """
    Search MusicBrainz for release, then fetch cover from Cover Art Archive.
    Returns high-quality official cover URL or None.
    """
    query = f'release:"{title}" AND artist:"{artist}"'
    params = {"query": query, "limit": 1, "fmt": "json"}
    time.sleep(1.1)  # MusicBrainz rate limit: max 1 req/sec
    data = _get(f"{MB_BASE}/release", params=params)
    if not data or not data.get("releases"):
        return None
    mbid = data["releases"][0].get("id")
    if not mbid:
        return None
    time.sleep(1.1)
    caa_data = _get(f"{CAA_BASE}/release/{mbid}")
    if not caa_data:
        return None
    images = caa_data.get("images", [])
    for img in images:
        if img.get("front"):
            return img.get("image") or (img.get("thumbnails", {}).get("500"))
    if images:
        return images[0].get("image") or (images[0].get("thumbnails", {}).get("500"))
    return None


def fetch_from_itunes(title: str, artist: str) -> Optional[str]:
    """
    Search iTunes for album and return artwork URL.
    Returns 500x500 artwork URL or None.
    """
    term = urllib.parse.quote(f"{title} {artist}")
    params = {"term": term, "entity": "album", "media": "music", "limit": 5}
    data = _get(f"{ITUNES_BASE}", params=params)
    if not data or not data.get("results"):
        return None
    # Find best match (fuzzy on collectionName and artistName)
    title_lower = title.lower()
    artist_lower = artist.lower()
    for r in data["results"]:
        col = (r.get("collectionName") or "").lower()
        art = (r.get("artistName") or "").lower()
        if title_lower in col or col in title_lower:
            if artist_lower in art or art in artist_lower:
                url = r.get("artworkUrl100")
                if url:
                    return _itunes_artwork_url(url, 500)
    # Fallback: first result if title/artist are close enough
    first = data["results"][0]
    url = first.get("artworkUrl100")
    if url:
        return _itunes_artwork_url(url, 500)
    return None


def fetch_cover_for_album(title: str, artist: str, year: Optional[int] = None) -> Optional[str]:
    """
    Fetch official album cover URL for the given title and artist.
    Tries: DodoApps Artwork API → iTunes → Cover Art Archive.
    Returns URL string or None.
    """
    if not title or not artist:
        return None
    title = title.strip()
    artist = artist.strip()
    if not title or not artist:
        return None
    url = fetch_from_dodo_artwork(title, artist)
    if url:
        return url
    url = fetch_from_itunes(title, artist)
    if url:
        return url
    url = fetch_from_cover_art_archive(title, artist)
    return url
