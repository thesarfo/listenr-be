"""
Fetch album descriptions from MusicBrainz annotations and Wikipedia.

Tries MusicBrainz release-group annotation first (when MBID available),
then Wikipedia intro paragraph. Both are free and require no API keys.
Returns (description, wikipedia_url) - url is set when source is Wikipedia.
"""
import re
import time
import urllib.parse
from typing import Optional, Tuple

import httpx

USER_AGENT = "Listenr/1.0 (https://github.com/listenr)"
MB_BASE = "https://musicbrainz.org/ws/2"
WIKI_API = "https://en.wikipedia.org/w/api.php"


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


def _strip_wiki_markup(text: str) -> str:
    """Remove basic MusicBrainz/wiki markup from annotation text."""
    if not text:
        return ""
    # Remove [[link|label]] -> label, [[link]] -> link
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    # Remove '''bold''' and ''italic''
    text = re.sub(r"'{2,3}([^']*)'{2,3}", r"\1", text)
    # Remove external links [http://... label]
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\]]+\]", "", text)
    return text.strip()


def fetch_from_musicbrainz(rgid: str) -> Optional[str]:
    """
    Fetch release-group annotation from MusicBrainz.
    Returns plain-text description or None.
    """
    if not rgid:
        return None
    time.sleep(1.1)  # Rate limit
    params = {"query": f"entity:{rgid}", "limit": 1, "fmt": "json"}
    data = _get(f"{MB_BASE}/annotation", params=params)
    if not data or not data.get("annotations"):
        return None
    ann = data["annotations"][0]
    text = ann.get("text", "").strip()
    if not text:
        return None
    text = _strip_wiki_markup(text)
    # Take first paragraph (up to first double newline) or first ~500 chars
    if "\n\n" in text:
        text = text.split("\n\n")[0]
    return text[:600].strip() if len(text) > 600 else text


def fetch_from_wikipedia(title: str, artist: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Search Wikipedia for album article and return (first paragraph, article URL).
    """
    if not title:
        return None, None
    # Search for album page
    search_term = f"{title} {artist} album"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": search_term,
        "srlimit": 5,
        "format": "json",
    }
    data = _get(WIKI_API, params=params)
    if not data or not data.get("query", {}).get("search"):
        return None, None
    # Prefer results where snippet mentions "album"
    search_results = data["query"]["search"]
    page_id = None
    for r in search_results:
        snippet = (r.get("snippet") or "").lower()
        if "album" in snippet or "studio album" in snippet:
            page_id = r.get("pageid")
            break
    if not page_id:
        page_id = search_results[0].get("pageid")
    if not page_id:
        return None, None
    # Fetch extract (intro) and page title
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": 1,
        "explaintext": 1,
        "exsectionformat": "plain",
        "pageids": page_id,
        "format": "json",
    }
    data = _get(WIKI_API, params=params)
    if not data:
        return None, None
    pages = data.get("query", {}).get("pages", {})
    page = pages.get(str(page_id), {})
    extract = (page.get("extract") or "").strip()
    if not extract:
        return None, None
    page_title = page.get("title", "")
    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}" if page_title else None
    first_para = extract.split("\n\n")[0].strip()
    desc = first_para[:600] if len(first_para) > 600 else first_para
    return desc, wiki_url


def fetch_description_for_album(
    title: str, artist: str, release_group_mbid: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch album description from MusicBrainz annotation or Wikipedia.
    Tries MusicBrainz first if release_group_mbid is provided.
    Returns (description, wikipedia_url). wikipedia_url is set only when from Wikipedia.
    """
    if not title:
        return None, None
    title = title.strip()
    artist = (artist or "").strip()
    desc = None
    wiki_url = None
    if release_group_mbid:
        desc = fetch_from_musicbrainz(release_group_mbid)
    if not desc:
        desc, wiki_url = fetch_from_wikipedia(title, artist)
    return desc, wiki_url
