"""Pixabay music/sound-effects acquisition (MD-06 support, quarantine-first).

Pixabay has no public API for audio (the documented API covers images and
videos only) and the pixabay.com pages sit behind a Cloudflare challenge
(verified 2026-10-23: HTTP 403 "Just a moment..." for plain programmatic
requests, including the bootstrap JSON). The content CDN — cdn.pixabay.com —
is separate and already serves the MP3 files to plain HTTP clients (verified
the same day: 200, valid MP3 frames). This module therefore offers explicit
acquisition paths:

1. **Direct** — try to fetch the search page programmatically. When the site
   shows the challenge, the error message tells the operator exactly what to
   do instead of retrying blindly.
2. **Page file** — the operator opens the Pixabay search page in their own
   browser, saves the HTML and passes it with ``--page-file``; the parser
   extracts candidate tracks (bootstrap JSON or the CDN MP3 fallback).
3. **Track list** — ``--tracks-file`` with CDN MP3 URLs taken from the
   browser DevTools network tab (one per line, optional "# title" comment);
   downloads from the open CDN then run fully unattended.

Downloads are never automatic: a fetched candidate list is printed and only
explicitly picked entries (``--pick 1,3``) are saved to
``brands/<slug>/imports/audio/`` — the same git-ignored, quarantined staging
area the brand scan uses. Every file lands with a report entry carrying the
Pixabay Content License facts and the source page; publishing a Pixabay asset
still requires a human review record in ``media/asset-library.json`` (the
library validator refuses anything without one).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .spec import ProjectError

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 "
              "Safari/537.36")
AUDIOS = {"music": "music", "sound-effects": "sound-effects"}
SEARCH_URL = "https://pixabay.com/pl/{kind}/search/{query}/"
LICENSE_FACTS = {
    "license": "Pixabay Content License",
    "license_url": "https://pixabay.com/service/license-summary/",
    "summary": ("Royalty-free, commercial use allowed, attribution not "
                "required; content may not be sold or redistributed "
                "standalone. Tracks registered in Content ID (shield icon "
                "on the site) can still trigger YouTube claims — prefer "
                "unmarked tracks for delivery. Content published before "
                "9 January 2019 is CC0."),
    "verified": "2026-10-23",
}
CHALLENGE_HINTS = ("just a moment", "cf-browser-verification",
                   "challenge-platform", "attention required")


class PixabayError(ProjectError):
    """Raised for blocked, unreadable or unparsable Pixabay access."""


def _challenge_message(url: str) -> str:
    return ("Pixabay showed a Cloudflare challenge (blocked automated "
            f"access to {url}). Open the page in your browser and either:\n"
            "  a) save the rendered page and rerun with --page-file <file>, "
            "or\n"
            "  b) export your cf_clearance cookie and pass it as "
            "--cookies 'cf_clearance=...'\n"
            "  c) copy cdn.pixabay.com MP3 urls from the browser network "
            "tab and rerun with --tracks-file <file>\n"
            "Do not retry blindly; respect the site's access terms.")


def http_get(url: str, *, cookies: str | None = None,
             timeout: int = 30) -> bytes:
    """Fetch a URL with a browser-like UA; raise PixabayError on challenge."""
    headers = {"User-Agent": USER_AGENT,
               "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.9"}
    if cookies:
        headers["Cookie"] = cookies
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            code = getattr(response, "status", response.getcode())
            if code != 200:
                raise PixabayError(f"Pixabay answered HTTP {code} for {url}")
            return response.read()
    except PixabayError:
        raise
    except HTTPError as exc:
        # Cloudflare answers plain clients with HTTP 403/503 challenge pages;
        # urllib raises before the body is read, so inspect it here and give
        # the operator the documented workarounds instead of a bare error.
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        if exc.code in (401, 403, 429, 503) or _looks_like_challenge(body):
            raise PixabayError(_challenge_message(url)) from exc
        raise PixabayError(f"Pixabay answered HTTP {exc.code} for {url}") from exc
    except Exception as exc:  # urllib errors are not uniformly typed
        raise PixabayError(f"Cannot fetch {url}: {exc}") from exc


def _looks_like_challenge(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in CHALLENGE_HINTS)


def search_page_url(query: str, kind: str = "music", *, lang: str = "pl") -> str:
    if kind not in AUDIOS:
        raise PixabayError(f"kind must be {sorted(AUDIOS)}, got {kind!r}")
    return SEARCH_URL.format(
        kind=AUDIOS[kind], query=query.strip().replace(" ", "-"))


def fetch_search_page(query: str, kind: str = "music", *, lang: str = "pl",
                      cookies: str | None = None) -> str:
    """Fetch a Pixabay search page; guide the operator past the challenge."""
    url = search_page_url(query, kind, lang=lang)
    body = http_get(url, cookies=cookies)
    text = body.decode("utf-8", "replace")
    if _looks_like_challenge(text):
        raise PixabayError(_challenge_message(url))
    return text


def _iter_values(payload) -> "list[dict]":
    """Recursively collect dicts from unknown bootstrap-JSON shapes."""
    found: list[dict] = []
    if isinstance(payload, dict):
        found.append(payload)
        for value in payload.values():
            found.extend(_iter_values(value))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(_iter_values(value))
    return found


def _pick(value):
    return re.sub(r"[-_]+", " ", value).strip()


def parse_tracks(source: str, base_url: str = "") -> list[dict]:
    """Parse candidate tracks from search-page HTML (bootstrap JSON first).

    The bootstrap JSON lives behind a URL embedded in the HTML. When it is
    missing the parser falls back to scanning the raw HTML for CDN MP3 urls;
    the fallback carries less metadata and that limitation is recorded.
    """
    if _looks_like_challenge(source):
        raise PixabayError(
            "Saved page is a Cloudflare challenge page, not search results; "
            "save the page after it fully renders")
    payload_url = None
    match = re.search(r"window\.__BOOTSTRAP_URL__\s*=\s*[\"']([^\"']+)[\"']",
                      source)
    if match:
        candidate = match.group(1)
        if candidate and not candidate.startswith("window"):
            payload_url = candidate
    tracks: dict[str, dict] = {}
    if payload_url:
        full = payload_url if payload_url.startswith("http") else (
            f"https://pixabay.com{payload_url}")
        payload = json.loads(http_get(full).decode("utf-8", "replace"))
        for item in _iter_values(payload):
            url = None
            if not isinstance(item, dict):
                continue
            for key in ("src", "audio_url", "audioUrl", "mp3_url", "mp3Url",
                        "audio", "stream_url", "streamUrl"):
                value = item.get(key)
                if isinstance(value, str) and "cdn.pixabay.com/audio" in value:
                    url = value.split("?")[0]
                    break
            if url is None:
                for value in item.values():
                    if (isinstance(value, str)
                            and value.startswith("https://cdn.pixabay.com/audio/")
                            and value.endswith(".mp3")):
                        url = value.split("?")[0]
                        break
            if not url:
                continue
            # Real bootstrap items carry a readable `filename` like
            # 'spy-always-dies-along-93740.mp3'; the download route they
            # advertise requires an account, the CDN src does not.
            name = item.get("filename") or item.get("title") or \
                item.get("name") or Path(urlsplit(url).path).stem
            title = _pick(re.sub(r"\.mp3$", "", str(name)))
            tracks[url] = {
                "title": title,
                "url": url,
                "page": (f"{base_url}#{item.get('id')}" if base_url
                         else "unknown-page"),
                "duration": item.get("duration") if isinstance(
                    item.get("duration"), (int, float)) else None,
                "source": "bootstrap-json",
            }
    if not tracks:
        # Fallback: scan the raw HTML for CDN MP3 urls. The download and
        # stream forms of the same file are treated as one candidate.
        for url in re.findall(
                r"https://cdn\.pixabay\.com/(?:download/)?audio/"
                r"[^\"'<>\\ ]+\.mp3", source):
            stem = Path(urlsplit(url).path).stem
            tracks.setdefault(stem, {
                "title": _pick(stem),
                "url": url.split("?")[0],
                "page": base_url or "unknown-page",
                "duration": None,
                "source": "html-fallback",
            })
    ordered = list(tracks.values())
    if not ordered:
        raise PixabayError(
            "No Pixabay audio candidates found on this page; the site layout "
            "may have changed — save a fully rendered page and retry")
    return ordered


def parse_track_list(source: str, *, base_page: str = "") -> list[dict]:
    """Build candidates from a plain list of CDN MP3 URLs (one per line).

    Copy the URLs from the browser DevTools network tab while playing the
    track (cdn.pixabay.com serves MP3s to plain HTTP clients — verified
    2026-10-23). Optionally give each line a title after an internal
    comment: ``https://cdn.pixabay.com/... # Spy Always Dies``; the title is
    otherwise derived from the file name.
    """
    tracks: list[dict] = []
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, _, comment = line.partition("#")
        url = url.strip()
        if not url:
            continue
        if ".pixabay.com" not in url or not url.endswith(".mp3"):
            raise PixabayError(
                f"Track list lines must be Pixabay MP3 urls: {url[:80]!r}")
        stem = Path(urlsplit(url).path).stem
        title = comment.strip() or _pick(stem)
        tracks.append({
            "title": title,
            "url": url.split("?")[0],
            "page": base_page or "unknown-page",
            "duration": None,
            "source": "tracks-file",
        })
    if not tracks:
        raise PixabayError("The track list contains no MP3 urls")
    return tracks


def download_candidates(tracks: list[dict], destination: Path, picks: str,
                        *, kind: str, cookies: str | None = None) -> dict:
    """Download only explicitly picked candidates into the quarantine area.

    MP3 delivery from cdn.pixabay.com requires no challenge (verified
    2026-10-23: 200 with valid MP3 frames), so pass ``cookies`` only when a
    page fetch needs the operator's browser context.
    """
    selection = []
    for token in picks.split(","):
        position = int(token.strip())
        if not 1 <= position <= len(tracks):
            raise PixabayError(
                f"Picked item {position} is outside 1..{len(tracks)}")
        selection.append(tracks[position - 1])
    destination = Path(destination)
    if "media" in destination.parts:
        raise PixabayError(
            "Guard: downloads belong in imports/ (quarantine), never "
            f"directly in media/: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "provider": "pixabay",
        "kind": kind,
        "license": dict(LICENSE_FACTS),
        "editorial_state": "quarantine",
        "note": ("Do not publish before a human review record is added to "
                 "media/asset-library.json with reviewed_by/review_date."),
        "files": [],
    }
    for track in selection:
        name = re.sub(r"[^A-Za-z0-9._-]+", "_",
                      track["title"].replace(" ", "_")) or "track"
        target = destination / f"pixabay_{name[:60]}.mp3"
        body = http_get(track["url"], cookies=cookies, timeout=120)
        if not body.startswith(b"ID3") and body[:2] not in (b"\xff\xfb",
                                                            b"\xff\xf3"):
            raise PixabayError(
                f"Downloaded payload for {track['url']!r} is not MP3 audio")
        target.write_bytes(body)
        entry = {
            "file": str(target),
            "title": track["title"],
            "source_url": track["page"],
            "audio_url": track["url"],
            "duration": track.get("duration"),
            "parsed_via": track["source"],
        }
        report["files"].append(entry)
    return report
