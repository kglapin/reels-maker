"""Fetch photographic demo assets with deterministic repository fallback.

Fixed known Unsplash CDN photo URLs, credited in provenance JSON. No API token.
Archived repository-owned raster cards are used only when CDN is unreachable.
"""
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from urllib.request import Request, urlopen
import io
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"examples"/"assets"
OUT.mkdir(parents=True,exist_ok=True)
PHOTO_URLS=[
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2",
]
FALLBACK=[
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_01.png",
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_04.png",
    ROOT/"archives/asta-energy/intermediates/subsidy_ad/card_07.png",
]
provenance=[]
for idx,(url,fallback) in enumerate(zip(PHOTO_URLS,FALLBACK),1):
    source="unsplash"
    try:
        request=Request(url,headers={"User-Agent":"ReelsMakerDemo/1.0"})
        with urlopen(request,timeout=12) as response:
            payload=response.read(8_000_000)
        photo=Image.open(io.BytesIO(payload)).convert("RGB")
        if min(photo.size)<600:
            raise ValueError("Insufficient remote photo resolution")
    except Exception as exc:
        source="repository_fallback"
        print(f"Photo {idx} unavailable: {exc!r}; fallback {fallback}")
        photo=Image.open(fallback).convert("RGB")
    frame=ImageOps.fit(photo,(720,820),method=Image.Resampling.LANCZOS,
                       centering=(.5,.45))
    frame=ImageEnhance.Contrast(frame).enhance(1.03)
    target=OUT/f"rotation-{idx:02d}.jpg"
    frame.save(target,quality=88,optimize=True)
    provenance.append({"index":idx,"source":source,
                       "original":url if source=="unsplash" else str(fallback.relative_to(ROOT)),
                       "license_note":"Unsplash License" if source=="unsplash" else "repository-owned test fixture"})
    print(target,source)
(OUT/"asset-provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
