"""Stock-media discovery, metadata and deterministic editorial composition planning.

No provider keys are embedded in source. Search is opt-in and uses official
APIs; downloaded media must be separately approved and tracked by license.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode
import json
import os
import urllib.request


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


def _json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def search_pexels(query: str, *, per_page: int = 12,
                  fetch: Callable = _json) -> list[StockAsset]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY is required")
    if not 1 <= per_page <= 80:
        raise ValueError("per_page must be 1..80")
    url = "https://api.pexels.com/v1/search?" + urlencode({
        "query": query, "per_page": per_page})
    payload = fetch(url, {"Authorization": key})
    return [StockAsset("pexels", str(p["id"]), p["src"]["medium"],
                       p["url"], p["photographer"], p["width"], p["height"],
                       p["src"]["original"], p["url"])
            for p in payload.get("photos", [])]


def search_pixabay(query: str, *, per_page: int = 12,
                   fetch: Callable = _json) -> list[StockAsset]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise RuntimeError("PIXABAY_API_KEY is required")
    if not 3 <= per_page <= 200:
        raise ValueError("Pixabay per_page must be 3..200")
    url = "https://pixabay.com/api/?" + urlencode({
        "key": key, "q": query, "image_type": "photo", "per_page": per_page,
        "safesearch": "true"})
    payload = fetch(url)
    return [StockAsset("pixabay", str(p["id"]), p["previewURL"],
                       p["pageURL"], p.get("user", "Unknown"),
                       p["imageWidth"], p["imageHeight"],
                       p.get("largeImageURL", p["webformatURL"]), p["pageURL"])
            for p in payload.get("hits", [])]


def search_unsplash(query: str, *, per_page: int = 12,
                    fetch: Callable = _json) -> list[StockAsset]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY is required")
    if not 1 <= per_page <= 30:
        raise ValueError("Unsplash per_page must be 1..30")
    url = "https://api.unsplash.com/search/photos?" + urlencode({
        "query": query, "per_page": per_page})
    payload = fetch(url, {"Authorization": "Client-ID " + key,
                          "Accept-Version": "v1"})
    return [StockAsset("unsplash", str(p["id"]), p["urls"]["small"],
                       p["links"]["html"], p["user"]["name"],
                       p["width"], p["height"], p["urls"]["full"],
                       p["user"]["links"]["html"])
            for p in payload.get("results", [])]


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
