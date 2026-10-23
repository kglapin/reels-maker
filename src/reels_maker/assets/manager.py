"""Asset manager with provenance, licence and editorial-state awareness.

Selection never treats an unreviewed clip as automatically clean. Finished
promos with burned-in graphics are excluded from overlay compositions unless a
caller explicitly opts in after human review.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image

from ..catalog import catalog
from ..ffmpeg import RenderError, execute, probe

VIDEO = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO = {".mp3", ".wav", ".m4a", ".aac"}

TOPIC_WORDS = {
    "pv": ("pv", "fotowolt", "solar", "panele", "dach", "dron"),
    "battery": ("magazyn", "battery", "bateria", "energii"),
    "heat": ("ciep", "heat", "pompa"),
    "installation": ("realizacja", "montaz", "montaż", "konstrukc", "pila",
                     "piła", "budzyn", "przedszkole"),
    "people": ("doradca", "klient", "zespol", "zespół", "biuro"),
    "product": ("produkt", "urzadzenie", "urządzenie", "falownik"),
    "city": ("miasto", "spoldzielnia", "spółdzielnia", "blok"),
}


@dataclass(frozen=True)
class Asset:
    path: Path
    kind: str
    relative: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    editorial_state: str = "unreviewed"
    burned_in: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    source: str = "brand"
    license: str = "brand-owned"
    dominant: tuple[int, int, int] | None = None

    @property
    def aspect(self) -> float | None:
        return self.width / self.height if self.width and self.height else None

    @property
    def overlay_ready(self) -> bool:
        return self.editorial_state == "clean_source"

    def to_dict(self) -> dict:
        return {
            "file": self.relative, "kind": self.kind,
            "size_bytes": self.size_bytes, "width": self.width,
            "height": self.height, "duration": self.duration,
            "aspect": round(self.aspect, 4) if self.aspect else None,
            "editorial_state": self.editorial_state,
            "overlay_ready": self.overlay_ready,
            "burned_in": list(self.burned_in),
            "topics": list(self.topics), "source": self.source,
            "license": self.license,
            "dominant_colour": list(self.dominant) if self.dominant else None,
        }


class AssetManager:
    def __init__(self, root: Path, brand: str | None = None):
        self.root = Path(root).resolve()
        self.brand = brand
        self.assets: list[Asset] = []
        self.reviews: dict[str, dict] = {}
        self.warnings: list[str] = []
        if brand:
            self.brand_root = self.root / "brands" / brand
            review_file = self.brand_root / "media" / "asset-reviews.json"
            if review_file.is_file():
                data = json.loads(review_file.read_text(encoding="utf-8"))
                self.reviews = data.get("assets", {})
            self._scan(self.brand_root)
        else:
            self.brand_root = self.root
            self._scan(self.root)

    def _scan(self, root: Path) -> None:
        if not root.is_dir():
            raise RenderError(f"Asset directory does not exist: {root}")
        result = catalog(root, include_metadata=False,
                         reviewed_assets=self.reviews)
        for item in result["items"]:
            path = root / item["file"]
            suffix = path.suffix.lower()
            kind = ("video" if suffix in VIDEO else
                    "audio" if suffix in AUDIO else "other")
            if kind == "other":
                continue
            review = self.reviews.get(item["file"], {})
            topics = self._topics(path.name)
            self.assets.append(Asset(
                path=path, kind=kind, relative=item["file"],
                size_bytes=item["size_bytes"],
                editorial_state=review.get("type", "unreviewed"),
                burned_in=tuple(review.get("burned_in", [])),
                topics=tuple(topics),
                license=review.get("license", "brand-owned")))
        # The catalog intentionally lists only audio/video. Photography and
        # logos are discovered here with the same provenance rules.
        import os
        for folder, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs
                             if d not in (".git", ".cache", ".venv", ".tmp",
                                          "renders", "__pycache__", "work")
                             and not d.startswith("."))
            for name in sorted(names):
                path = Path(folder) / name
                if path.suffix.lower() not in IMAGE or not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                review = self.reviews.get(relative, {})
                self.assets.append(Asset(
                    path=path, kind="image", relative=relative,
                    size_bytes=path.stat().st_size,
                    editorial_state=review.get("type", "unreviewed"),
                    burned_in=tuple(review.get("burned_in", [])),
                    topics=tuple(self._topics(path.name)),
                    license=review.get("license", "brand-owned")))

    @staticmethod
    def _topics(name: str) -> list[str]:
        lowered = name.lower()
        result = []
        for topic, words in TOPIC_WORDS.items():
            if any(word in lowered for word in words):
                result.append(topic)
        return result

    def enrich(self, asset: Asset, *,
               dominant: bool = False) -> Asset:
        if asset.kind == "image":
            with Image.open(asset.path) as image:
                width, height = image.size
                colour = None
                if dominant:
                    reduced = image.convert("RGB").resize((16, 16))
                    pixels = list(reduced.getdata())
                    colour = tuple(round(sum(channel) / len(pixels))
                                   for channel in zip(*pixels))
            return Asset(**{**asset.__dict__, "width": width, "height": height,
                            "dominant": colour})
        if asset.kind == "video":
            info = probe(asset.path)
            video = next((stream for stream in info.get("streams", [])
                          if stream.get("codec_type") == "video"), None)
            if video is None:
                raise RenderError(f"No video stream: {asset.path}")
            colour = None
            if dominant:
                still = self.still(asset, 0.5)
                with Image.open(still) as image:
                    reduced = image.convert("RGB").resize((16, 16))
                    pixels = list(reduced.getdata())
                    colour = tuple(round(sum(channel) / len(pixels))
                                   for channel in zip(*pixels))
            return Asset(**{**asset.__dict__,
                            "width": int(video["width"]),
                            "height": int(video["height"]),
                            "duration": float(info["format"].get("duration", 0)),
                            "dominant": colour})
        return asset

    def select(self, kind: str = "video", *, topic: str | None = None,
               min_width: int = 0, exclude: Iterable[Path | str] = (),
               allow_unknown: bool = False,
               allow_prebranded: bool = False,
               seed: int = 0) -> Asset:
        """Deterministically pick a suitable, provenance-checked asset."""
        excluded = {Path(item).resolve() if isinstance(item, (str, Path))
                    else item for item in exclude}
        candidates = [asset for asset in self.assets if asset.kind == kind
                      and asset.path.resolve() not in excluded]
        if kind == "video":
            # Probe only candidates; resolution filtering needs metadata.
            candidates = [self.enrich(asset, dominant=False)
                          for asset in candidates]
            candidates = [asset for asset in candidates
                          if (asset.width or 0) >= min_width]
        if topic:
            candidates = [asset for asset in candidates
                          if topic in asset.topics]
        clean = []
        for asset in candidates:
            if asset.editorial_state == "finished_promo" and not allow_prebranded:
                continue
            if asset.editorial_state == "unreviewed" and not allow_unknown:
                continue
            clean.append(asset)
        if not clean and candidates and allow_unknown:
            clean = [asset for asset in candidates
                     if asset.editorial_state != "finished_promo"]
        if not clean:
            raise RenderError(
                "No approved asset matches the request. "
                f"kind={kind} topic={topic} min_width={min_width}")
        # Prefer high resolution, reviewed clean source, then stable rotation.
        clean.sort(key=lambda asset: (
            asset.overlay_ready, asset.width or 0, asset.height or 0,
            asset.relative))
        top = clean[:min(3, len(clean))]
        return top[seed % len(top)]

    def still(self, asset: Asset, time: float = 0.0,
              width: int = 1080) -> Path:
        """Extract or reuse a deterministic still for photo/camera motion."""
        if time < 0:
            raise ValueError("Still time must be nonnegative")
        cache = self.root / ".cache" / "reels-maker" / "stills"
        cache.mkdir(parents=True, exist_ok=True)
        signature = hashlib.sha1(
            f"{asset.path.resolve()}:{asset.path.stat().st_mtime_ns}:"
            f"{time:.3f}:{width}".encode()).hexdigest()
        destination = cache / f"{signature}.png"
        if destination.is_file() and destination.stat().st_size > 0:
            return destination
        if asset.kind == "image":
            with Image.open(asset.path) as image:
                image = image.convert("RGB")
                ratio = width / image.width
                image = image.resize((width, max(1, round(image.height * ratio))),
                                     Image.Resampling.LANCZOS)
                image.save(destination)
            return destination
        execute(["-ss", f"{time:.3f}", "-i", str(asset.path), "-frames:v", "1",
                 "-vf", f"scale={width}:-2:flags=lanczos", "-q:v", "2",
                 str(destination)])
        if not destination.is_file():
            raise RenderError(f"Could not extract still from {asset.path}")
        return destination

    def summary(self) -> dict:
        by_kind: dict[str, int] = {}
        for asset in self.assets:
            by_kind[asset.kind] = by_kind.get(asset.kind, 0) + 1
        return {"root": str(self.root), "brand": self.brand,
                "count": len(self.assets), "by_kind": by_kind,
                "warnings": list(self.warnings)}

    def to_dict(self) -> dict:
        return {"summary": self.summary(),
                "assets": [asset.to_dict() for asset in self.assets]}
