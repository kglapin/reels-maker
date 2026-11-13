"""Verified Google Fonts supply for brand projects.

``fetch-fonts`` installs hash-pinned, latin-ext-complete files into a
brand's ``media/fonts`` directory. Static families download per-weight
TTFs; variable families download one file per style and instantiate
static weights locally with fontTools, so renders never depend on
machine-local installs or silent fallback fonts.
"""
from __future__ import annotations

import hashlib
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

from .textkit.typesetter import WEIGHT_SUFFIXES

ALLOWLIST_PATH = (Path(__file__).resolve().parent / "design" /
                  "google_fonts_allowlist.json")

WEIGHT_VALUES = {
    "light": 300,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
}

ITALIC_WEIGHT_VALUES = {
    "italic": 400,
    "bold_italic": 700,
}


def _key(family: str) -> str:
    return family.lower().replace(" ", "")


def load_allowlist(path: str | Path | None = None) -> dict:
    location = Path(path) if path else ALLOWLIST_PATH
    try:
        return json.loads(location.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Font allowlist not found: {location}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Font allowlist is not valid JSON: {location} ({exc})") from exc


def _families(allowlist: dict) -> dict:
    families = allowlist.get("families") or {}
    return {_key(name): (name, entry) for name, entry in families.items()}


def _download(url: str, timeout: int) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Cannot download font file: {url} ({exc})")


def _verify(data: bytes, sha256: str, url: str) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256.lower():
        raise RuntimeError(
            f"Font checksum mismatch for {url}: refusing to install")


def _instantiate(data: bytes, coordinates: dict) -> bytes:
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    font = TTFont(io.BytesIO(data))
    try:
        # instantiateVariableFont returns a new font unless inplace=True;
        # saving the input would keep the unpinned variable default.
        instantiated = instantiateVariableFont(
            font, coordinates, updateFontNames=True)
        target = instantiated if instantiated is not None else font
        try:
            buffer = io.BytesIO()
            target.save(buffer)
        finally:
            if target is not font:
                target.close()
    finally:
        font.close()
    return buffer.getvalue()


def _save(dest_dir: Path, stem: str, weight: str, data: bytes) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"{stem}-{WEIGHT_SUFFIXES[weight]}.ttf"
    target.write_bytes(data)
    return target


def _static_files(entry: dict, wanted: list[str] | None) -> list[str]:
    available = entry.get("files") or {}
    if wanted is None:
        return [w for w in WEIGHT_SUFFIXES if w in available]
    unknown = [w for w in wanted if w not in available]
    if unknown:
        raise RuntimeError(
            f"Weights not available for this family: {', '.join(unknown)}")
    return list(wanted)


def fetch_font(family: str, dest_dir: str | Path,
               weights: list[str] | None = None,
               allowlist: dict | None = None,
               timeout: int = 60) -> list[Path]:
    """Download, verify and install one family into ``dest_dir``."""
    catalogue = _families(load_allowlist() if allowlist is None
                          else allowlist)
    found = catalogue.get(_key(family))
    if found is None:
        available = sorted(name for name, _ in catalogue.values())
        raise RuntimeError(
            f"Font family '{family}' is not in the verified allowlist. "
            f"Available: {', '.join(available)}")
    _, entry = found
    stem = _.replace(" ", "")
    dest = Path(dest_dir)
    saved: list[Path] = []
    if entry.get("kind") == "variable":
        source = entry["source"]
        data = _download(source["url"], timeout)
        _verify(data, source["sha256"], source["url"])
        values = source.get("wght") or sorted(WEIGHT_VALUES.values())
        by_value = {value: name for name, value in WEIGHT_VALUES.items()}
        wanted = [by_value[v] for v in values if v in by_value]
        if weights is not None:
            unknown = [w for w in weights if w not in wanted
                       and w not in ITALIC_WEIGHT_VALUES]
            if unknown:
                raise RuntimeError(
                    "Weights not available for this family: "
                    f"{', '.join(unknown)}")
            wanted = [w for w in wanted if w in weights]
        from fontTools.ttLib import TTFont as _TTFont
        probe = _TTFont(io.BytesIO(data), lazy=True)
        try:
            axes = ({a.axisTag for a in probe["fvar"].axes}
                    if "fvar" in probe else set())
        finally:
            probe.close()
        coordinates: dict = {}
        for weight in wanted:
            point = dict(coordinates)
            point["wght"] = WEIGHT_VALUES[weight]
            if "wdth" in axes:
                point["wdth"] = 100
            saved.append(_save(dest, stem, weight,
                               _instantiate(data, point)))
        italic = entry.get("italic_source")
        italic_wanted = [w for w in ("italic", "bold_italic")
                         if weights is None or w in weights]
        if italic and italic_wanted:
            idata = _download(italic["url"], timeout)
            _verify(idata, italic["sha256"], italic["url"])
            for weight in italic_wanted:
                saved.append(_save(dest, stem, weight, _instantiate(
                    idata, {"wght": ITALIC_WEIGHT_VALUES[weight]})))
        return sorted(saved)
    wanted_static = _static_files(entry, weights)
    for weight in wanted_static:
        ref = entry["files"][weight]
        data = _download(ref["url"], timeout)
        _verify(data, ref["sha256"], ref["url"])
        saved.append(_save(dest, stem, weight, data))
    return sorted(saved)


def fetch_brand_fonts(brand: str, root: str | Path,
                      family: str | None = None,
                      weights: list[str] | None = None,
                      allowlist: dict | str | Path | None = None,
                      timeout: int = 60) -> dict:
    """Install a brand's primary family into brands/<slug>/media/fonts."""
    from .brand import brand_directory
    from .spec import ProjectError
    brand_dir = Path(brand_directory(brand, root))
    manifest = brand_dir / "brand.json"
    if not manifest.is_file():
        raise ProjectError(f"Unknown brand: {brand}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    typography = (data.get("identity") or {}).get("typography") or {}
    resolved = (family or typography.get("primary") or "").strip()
    if not resolved:
        raise ProjectError(
            f"Brand '{brand}' declares no typography.primary and no "
            f"--family was given")
    table = load_allowlist(allowlist) if isinstance(
        allowlist, (str, Path)) else allowlist
    saved = fetch_font(resolved, brand_dir / "media" / "fonts",
                       weights=weights, allowlist=table, timeout=timeout)
    return {
        "status": "ok",
        "brand": brand,
        "family": resolved,
        "weights": [path.stem.rsplit("-", 1)[-1] for path in saved],
        "files": [str(path) for path in saved],
        "dir": str(brand_dir / "media" / "fonts"),
    }
