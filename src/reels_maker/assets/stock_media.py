"""Stock-media discovery, metadata and deterministic editorial composition planning.

No provider keys are embedded in source. Search is opt-in and uses official
APIs; downloaded media must be separately approved and tracked by license.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from datetime import date
from typing import Callable
from urllib.parse import urlencode
import json
import os
import re
import urllib.request
from .provider_client import provider_json


def _provider_fetch(provider: str, url: str, headers: dict | None,
                    fetch: Callable | None, *, cache_response: bool = True,
                    retries: int | None = None) -> dict:
    # Injected fetchers are deliberately a test seam. Normal calls share provider
    # quotas, retries and metadata cache through ProviderClient.
    return (fetch(url, headers) if fetch is not None else
            provider_json(provider, url, headers,
                          cache_response=cache_response, retries=retries))


@dataclass(frozen=True)
class StockRendition:
    url: str
    width: int
    height: int
    file_type: str
    quality: str = ""
    fps: float | None = None
    size_bytes: int | None = None


@dataclass(frozen=True)
class StockAsset:
    provider: str
    asset_id: str
    preview_url: str
    source_url: str
    author: str
    width: int
    height: int
    download_url: str
    attribution_url: str
    media_type: str = "image"
    license: str = ""
    license_url: str = ""
    attribution: str = ""
    tracking_url: str = ""
    duration_seconds: int | None = None
    renditions: tuple[StockRendition, ...] = ()
    rights_status: str = "unknown"
    provider_url: str = ""
    rights_decision: dict | None = None

    def provenance(self) -> dict:
        """Machine-readable source evidence; provider metadata is not clearance."""
        return {
            "provider": self.provider, "asset_id": self.asset_id,
            "provider_url": self.provider_url, "source_url": self.source_url,
            "author": self.author,
            "license": self.license, "license_url": self.license_url,
            "attribution": self.attribution, "media_type": self.media_type,
            "rights_status": self.rights_status,
            "rights_decision": self.rights_decision,
        }


def apply_reviewed_rights_decision(asset: StockAsset, policy: dict) -> StockAsset:
    """Apply an explicit item-specific human review; search evidence never clears rights.

    Policy must bind provider+asset ID and state the reviewer, decision and evidence.
    This function records the decision without interpreting license text.
    """
    required = {"provider", "asset_id", "download_url", "source_url",
                "decision", "reviewer", "review_date", "evidence", "attribution"}
    if not isinstance(policy, dict) or not required.issubset(policy):
        raise ValueError("Reviewed rights policy must bind provider, asset_id, source_url and download_url, and include reviewer, date, decision and evidence")
    if policy["provider"] != asset.provider or str(policy["asset_id"]) != asset.asset_id:
        raise ValueError("Rights decision must identify this exact provider asset")
    if policy["download_url"] != asset.download_url or policy["source_url"] != asset.source_url:
        raise ValueError("Rights decision must bind this exact source and download URL")
    if not asset.source_url or not asset.download_url:
        raise ValueError("Rights decisions require non-empty source and download URLs")
    if not all(isinstance(policy[key], str) and policy[key].strip()
               for key in ("reviewer", "review_date", "evidence", "attribution")):
        raise ValueError("Rights decision reviewer, review_date, evidence and attribution must be non-empty text")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", policy["review_date"]):
        raise ValueError("Rights decision review_date must be ISO YYYY-MM-DD")
    try:
        date.fromisoformat(policy["review_date"])
    except ValueError as exc:
        raise ValueError("Rights decision review_date must be ISO YYYY-MM-DD") from exc
    if policy["decision"] not in ("cleared", "blocked", "unknown"):
        raise ValueError("Rights decision must be cleared, blocked or unknown")
    from dataclasses import replace
    decision = dict(policy)
    license_name = str(policy.get("license") or asset.license).strip()
    license_url = str(policy.get("license_url") or asset.license_url).strip()
    platforms = policy.get("allowed_platforms", [])
    if policy["decision"] == "cleared":
        if (not license_name or license_name.lower() == "unknown"
                or not license_url.startswith("https://")):
            raise ValueError("Cleared assets need an explicit license name and HTTPS URL")
        if not isinstance(platforms, list) or not platforms or not all(
                isinstance(item, str) and item.strip() for item in platforms):
            raise ValueError("Cleared assets need explicitly allowed platforms")
    elif not isinstance(platforms, list) or not all(
            isinstance(item, str) and item.strip() for item in platforms):
        raise ValueError("allowed_platforms must be a list of explicit platform names")
    decision["license"] = license_name or "unknown"
    decision["license_url"] = license_url or "unknown"
    decision["allowed_platforms"] = list(platforms)
    return replace(asset, rights_status=policy["decision"],
                   license=license_name or asset.license,
                   license_url=license_url or asset.license_url,
                   attribution=policy["attribution"],
                   rights_decision=decision)


def _best_rendition(renditions: list[StockRendition]) -> StockRendition:
    if not renditions:
        raise ValueError("Provider returned no usable media renditions")
    return max(renditions, key=lambda item: (
        item.file_type.lower() == "video/mp4",
        item.width * item.height,
        item.height,
        item.width,
    ))


def _json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def _plain_text(value: object) -> str:
    """Strip provider-supplied markup before exposing metadata to reports/UI."""
    text = unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def search_pexels(query: str, *, per_page: int = 12,
                  fetch: Callable | None = None) -> list[StockAsset]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is required")
    if not 1 <= per_page <= 80:
        raise ValueError("per_page must be 1..80")
    url = "https://api.pexels.com/v1/search?" + urlencode({
        "query": query, "per_page": per_page})
    payload = _provider_fetch("pexels", url, {"Authorization": key}, fetch)
    return [StockAsset("pexels", str(p["id"]), p["src"]["medium"],
                       p["url"], p["photographer"], p["width"], p["height"],
                       p["src"]["original"], p["url"],
                       license="Pexels License",
                       license_url="https://www.pexels.com/license/",
                       attribution="API use requires a prominent Pexels link; credit the photographer when possible.",
                       provider_url="https://www.pexels.com")
            for p in payload.get("photos", [])]


def search_pexels_videos(query: str, *, per_page: int = 12,
                          orientation: str | None = None,
                          fetch: Callable | None = None) -> list[StockAsset]:
    """Search the official Pexels video API; results remain uncleared candidates."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is required")
    if not 1 <= per_page <= 80:
        raise ValueError("per_page must be 1..80")
    if orientation not in (None, "landscape", "portrait", "square"):
        raise ValueError("orientation must be landscape, portrait, square, or None")
    params = {"query": query, "per_page": per_page}
    if orientation:
        params["orientation"] = orientation
    url = "https://api.pexels.com/v1/videos/search?" + urlencode(params)
    payload = _provider_fetch("pexels", url, {"Authorization": key}, fetch)
    results = []
    for video in payload.get("videos", []):
        renditions = [StockRendition(
            str(file.get("link", "")), int(file.get("width") or 0),
            int(file.get("height") or 0), str(file.get("file_type", "")),
            str(file.get("quality", "")),
            float(file["fps"]) if file.get("fps") is not None else None,
        ) for file in video.get("video_files", []) if file.get("link")]
        if not renditions:
            continue
        best = _best_rendition(renditions)
        user = video.get("user") or {}
        results.append(StockAsset(
            "pexels", str(video.get("id", "")), str(video.get("image", "")),
            str(video.get("url", "")), str(user.get("name") or "Unknown"),
            int(video.get("width") or best.width),
            int(video.get("height") or best.height), best.url,
            str(user.get("url") or video.get("url", "")),
            license="Pexels License",
            license_url="https://www.pexels.com/license/",
            attribution="API use requires a prominent Pexels link; credit the videographer when possible.",
            provider_url="https://www.pexels.com",
            media_type="video", duration_seconds=int(video.get("duration") or 0),
            renditions=tuple(renditions),
        ))
    return results


def search_pixabay(query: str, *, per_page: int = 12,
                   fetch: Callable | None = None) -> list[StockAsset]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise RuntimeError("PIXABAY_API_KEY is required")
    if not 3 <= per_page <= 200:
        raise ValueError("Pixabay per_page must be 3..200")
    url = "https://pixabay.com/api/?" + urlencode({
        "key": key, "q": query, "image_type": "photo", "per_page": per_page,
        "safesearch": "true"})
    payload = _provider_fetch("pixabay", url, None, fetch)
    return [StockAsset("pixabay", str(p["id"]), p["previewURL"],
                       p["pageURL"], p.get("user", "Unknown"),
                       p["imageWidth"], p["imageHeight"],
                       (p.get("largeImageURL") or p.get("webformatURL") or p["previewURL"]), p["pageURL"],
                       license="Pixabay Content License",
                       license_url="https://pixabay.com/service/license-summary/",
                       attribution="API use requires a prominent Pixabay link; verify item-level third-party rights.",
                       provider_url="https://pixabay.com")
            for p in payload.get("hits", [])]


def search_pixabay_videos(query: str, *, per_page: int = 20,
                          fetch: Callable | None = None) -> list[StockAsset]:
    """Search Pixabay's official video endpoint; results are candidates only."""
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise RuntimeError("PIXABAY_API_KEY is required")
    if not 3 <= per_page <= 200:
        raise ValueError("Pixabay per_page must be 3..200")
    url = "https://pixabay.com/api/videos/?" + urlencode({
        "key": key, "q": query, "per_page": per_page, "safesearch": "true"})
    payload = _provider_fetch("pixabay", url, None, fetch)
    results = []
    for video in payload.get("hits", []):
        renditions = [StockRendition(
            str(item.get("url", "")), int(item.get("width") or 0),
            int(item.get("height") or 0), "video/mp4", str(name),
            size_bytes=int(item["size"]) if item.get("size") is not None else None,
        ) for name, item in (video.get("videos") or {}).items() if item.get("url")]
        if not renditions:
            continue
        best = _best_rendition(renditions)
        source_url = str(video.get("pageURL", ""))
        results.append(StockAsset(
            "pixabay", str(video.get("id", "")),
            str((video.get("videos") or {}).get("tiny", {}).get("thumbnail", "")),
            source_url, str(video.get("user") or "Unknown"),
            int(video.get("imageWidth") or best.width),
            int(video.get("imageHeight") or best.height), best.url, source_url,
            media_type="video", license="Pixabay Content License",
            license_url="https://pixabay.com/service/license-summary/",
            attribution="API use requires a prominent Pixabay link; verify item-level third-party rights.",
            provider_url="https://pixabay.com",
            duration_seconds=int(video.get("duration") or 0),
            renditions=tuple(renditions),
        ))
    return results


def search_unsplash(query: str, *, per_page: int = 12,
                    fetch: Callable | None = None) -> list[StockAsset]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY is required")
    if not 1 <= per_page <= 30:
        raise ValueError("Unsplash per_page must be 1..30")
    url = "https://api.unsplash.com/search/photos?" + urlencode({
        "query": query, "per_page": per_page})
    payload = _provider_fetch("unsplash", url, {"Authorization": "Client-ID " + key,
                          "Accept-Version": "v1"}, fetch)
    return [StockAsset("unsplash", str(p["id"]), p["urls"]["small"],
                        p["links"]["html"], p["user"]["name"],
                        p["width"], p["height"], p["urls"]["full"],
                        p["user"]["links"]["html"],
                        license="Unsplash License",
                        license_url="https://unsplash.com/license",
                        attribution="API use requires photographer and Unsplash attribution and image hotlinking.",
                        provider_url="https://unsplash.com",
                        tracking_url=p.get("links", {}).get("download_location", ""))
            for p in payload.get("results", [])]


def track_unsplash_download(asset: StockAsset, *, fetch: Callable | None = None) -> dict:
    """Notify Unsplash when a result is actually selected for use/download.

    Search itself does not count as a download. The returned image URL remains
    the provider's image URL for hotlink-compliant display/use.
    """
    if asset.provider != "unsplash" or not asset.tracking_url:
        raise ValueError("Asset has no Unsplash download-tracking URL")
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY is required")
    # Tracking is an action, not a search result: don't cache it or retry it.
    return _provider_fetch(
        "unsplash", asset.tracking_url,
        {"Authorization": "Client-ID " + key, "Accept-Version": "v1"},
        fetch, cache_response=False, retries=0)


def search_wikimedia_commons(query: str, *, per_page: int = 12,
                             fetch: Callable | None = None) -> list[StockAsset]:
    """Search Commons files and return imageinfo/extmetadata as candidates."""
    if not 1 <= per_page <= 50:
        raise ValueError("per_page must be 1..50")
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": per_page,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": 640,
    })
    payload = _provider_fetch("wikimedia_commons", url, {"User-Agent": "reels-maker/1.0 (media candidate search)"}, fetch)
    pages = payload.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        def value(name: str) -> str:
            item = meta.get(name, {})
            return _plain_text(item.get("value", "")) if isinstance(item, dict) else ""
        file_url = info.get("descriptionurl", "")
        results.append(StockAsset(
            "wikimedia_commons", str(page.get("pageid", "")),
            info.get("thumburl", info.get("url", "")), file_url,
            value("Artist") or "Unknown", int(info.get("width", 0)),
            int(info.get("height", 0)), info.get("url", ""), file_url,
            license=value("LicenseShortName") or value("License"),
            license_url=value("LicenseUrl"), attribution=value("Attribution"),
            provider_url="https://commons.wikimedia.org"))
    return results


def search_openverse(query: str, *, per_page: int = 12,
                     fetch: Callable | None = None) -> list[StockAsset]:
    """Search Openverse images; license fields are evidence, not clearance."""
    if not 1 <= per_page <= 20:
        raise ValueError("per_page must be 1..20")
    url = "https://api.openverse.org/v1/images/?" + urlencode({
        "q": query, "page_size": per_page})
    payload = _provider_fetch("openverse", url, {"User-Agent": "reels-maker/1.0 (media candidate search)"}, fetch)
    results = []
    for item in payload.get("results", []):
        results.append(StockAsset(
            "openverse", str(item.get("id", "")),
            item.get("thumbnail", ""), item.get("foreign_landing_url", ""),
            _plain_text(item.get("creator") or "Unknown"), int(item.get("width") or 0),
            int(item.get("height") or 0), item.get("url", ""),
            item.get("foreign_landing_url", ""),
            license=item.get("license", ""),
            license_url=item.get("license_url", ""),
            attribution=_plain_text(item.get("attribution", "")),
            provider_url="https://openverse.org"))
    return results


def rank_assets(assets: list[StockAsset], *, aspect: float,
                min_width: int = 900, min_height: int = 900) -> list[StockAsset]:
    """Rank by usable resolution and framing cost, never by provider priority."""
    if aspect <= 0:
        raise ValueError("Target aspect must be positive")
    def score(asset: StockAsset) -> tuple[float, str]:
        ratio = asset.width / max(1, asset.height)
        import math
        crop_loss = abs(math.log(ratio / aspect))
        resolution_penalty = (max(0, min_width - asset.width) / min_width
                              + max(0, min_height - asset.height) / min_height)
        return (crop_loss + 2*resolution_penalty, asset.asset_id)
    return sorted(assets, key=score)


def composition_candidates(image_width: int, image_height: int,
                           canvas_width: int, canvas_height: int,
                           *, focal_x: float = .5, focal_y: float = .5,
                           text_side: str = "left") -> list[dict]:
    """Generate several *different* crop/layout options for editorial review.

    The focal point is explicit; a later vision stage can estimate it. The
    function never pretends to have detected a face or subject automatically.
    """
    if min(image_width, image_height, canvas_width, canvas_height) <= 0:
        raise ValueError("Image and canvas dimensions must be positive")
    if not (0 <= focal_x <= 1 and 0 <= focal_y <= 1):
        raise ValueError("Focal coordinates must be normalized")
    if text_side not in ("left", "right"):
        raise ValueError("text_side must be left or right")
    W, H = canvas_width, canvas_height
    margin = round(W * .075)
    gap = round(W * .035)
    safe_width = W - 2*margin
    text_width = round(safe_width * .43)
    media_width = safe_width - text_width - gap
    image_x = margin + text_width + gap if text_side == "left" else margin
    layouts = [
        ("full_bleed", (0, 0, W, H), "overlay"),
        ("editorial_split", (image_x, round(H*.16), media_width,
                              round(H*.68)), "adjacent"),
        ("hero_window", (margin, round(H*.27), safe_width,
                          round(H*.48)), "above"),
        ("offset_portrait", (round(W*.19), round(H*.10),
                             round(W*.73), round(H*.71)), "outside"),
        ("cinematic_strip", (margin, round(H*.34), safe_width,
                             round(H*.31)), "above_below"),
    ]
    results = []
    for name, (x,y,w,h), placement in layouts:
        target_ratio = w/h
        source_ratio = image_width/image_height
        if source_ratio > target_ratio:
            crop_h = image_height
            crop_w = round(crop_h * target_ratio)
        else:
            crop_w = image_width
            crop_h = round(crop_w / target_ratio)
        crop_w = min(image_width, max(1,crop_w))
        crop_h = min(image_height, max(1,crop_h))
        left = max(0, min(image_width-crop_w,
                          round(image_width*focal_x - crop_w/2)))
        top = max(0, min(image_height-crop_h,
                         round(image_height*focal_y - crop_h/2)))
        retained = (crop_w*crop_h)/(image_width*image_height)
        results.append({"layout":name,"image_rect":[x,y,w,h],
                        "crop":[left,top,crop_w,crop_h],
                        "focal_point":[focal_x,focal_y],
                        "text_placement":placement,
                        "retained_fraction":round(retained,4)})
    return results
