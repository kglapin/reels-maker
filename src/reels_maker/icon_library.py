"""Version-pinned, sanitized SVG assets for the native renderer.

Icons are downloaded only on a cache miss; subsequent renders use on-disk
copies, never hotlinked graphics. Names are strict slugs (no path traversal).
The source SVG is vetted before passing it to CairoSVG: no scripts, external
references, embedded images, CSS or XML entity declarations.
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
import os
import re
import hashlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image

VERSIONS = {
    "lucide": "0.468.0",
    "heroicons": "v2.2.0",
    "tabler": "v3.49.0",
    "phosphor": "v2.0.8",
    "material_symbols": "10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7",
}
STYLES = {
    "lucide": ("outline",),
    "heroicons": ("outline", "solid"),
    "tabler": ("outline", "filled"),
    "phosphor": ("thin", "light", "regular", "bold", "fill", "duotone"),
    "material_symbols": ("outlined", "rounded", "sharp"),
}
DEFAULT_STYLES = {"lucide": "outline", "heroicons": "outline",
                  "tabler": "outline", "phosphor": "regular",
                  "material_symbols": "outlined"}
SEMANTIC_ICONS = {
    "lucide": {"battery": "battery-charging", "sun": "sun", "house": "house",
               "arrow": "arrow-right", "check": "check", "calendar": "calendar-days",
               "clock": "clock", "phone": "smartphone", "shield": "shield-check", "heat": "waves"},
    "heroicons": {"battery": "battery-100", "sun": "sun", "house": "home",
                  "arrow": "arrow-right", "check": "check", "calendar": "calendar-days",
                  "clock": "clock", "phone": "device-phone-mobile", "shield": "shield-check", "heat": "fire"},
    "tabler": {"battery": "battery-charging", "sun": "sun", "house": "home",
               "arrow": "arrow-right", "check": "check", "calendar": "calendar",
               "clock": "clock", "phone": "device-mobile", "shield": "shield-check", "heat": "flame"},
    "phosphor": {"battery": "battery-charging", "sun": "sun", "house": "house",
                 "arrow": "arrow-right", "check": "check", "calendar": "calendar-blank",
                 "clock": "clock", "phone": "device-mobile", "shield": "shield-check", "heat": "fire"},
    "material_symbols": {"battery": "web/battery_charging_full", "sun": "web/sunny",
                         "house": "web/home", "arrow": "web/arrow_right_alt",
                         "check": "web/check", "calendar": "web/calendar_month",
                         "clock": "web/schedule", "phone": "web/smartphone",
                         "shield": "web/shield", "heat": "web/local_fire_department"},
}
SEMANTIC_ROLES = tuple(SEMANTIC_ICONS["lucide"])
SEMANTIC_ALIASES = {"solar": "sun", "photovoltaic": "sun", "pv": "sun",
                    "home": "house", "storage": "battery", "battery storage": "battery",
                    "mobile": "phone", "heating": "heat", "temperature": "heat"}
LICENSES = {
    "lucide": {"id": "ISC", "url": "https://github.com/lucide-icons/lucide/blob/0.468.0/LICENSE", "notice_required": True,
                "additional_notice": "Some Feather-derived glyphs may retain MIT notices; preserve per-source notices where applicable."},
    "heroicons": {"id": "MIT", "url": "https://github.com/tailwindlabs/heroicons/blob/v2.2.0/LICENSE", "notice_required": True},
    "tabler": {"id": "MIT", "url": "https://github.com/tabler/tabler-icons/blob/v3.49.0/LICENSE", "notice_required": True},
    "phosphor": {"id": "MIT", "url": "https://github.com/phosphor-icons/core/blob/v2.0.8/LICENSE", "notice_required": True},
    "material_symbols": {"id": "Apache-2.0", "url": "https://github.com/google/material-design-icons/blob/10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7/LICENSE", "notice_required": True},
}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
MATERIAL_NAME_PATTERN = re.compile(r"^web/[a-z0-9]+(?:_[a-z0-9]+)*$")
HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
SVG = "{http://www.w3.org/2000/svg}"
ALLOWED_TAGS = {"svg", "g", "path", "circle", "rect", "line",
                "polyline", "polygon", "ellipse", "defs", "clipPath"}
ALLOWED_ATTRS = {"xmlns", "viewBox", "width", "height", "fill",
                 "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
                 "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
                 "fill-rule", "clip-rule", "d", "cx", "cy", "r", "rx",
                 "ry", "x", "y", "x1", "y1", "x2", "y2", "points",
                 "opacity", "transform", "id", "clip-path", "fill-opacity",
                 "stroke-opacity", "aria-hidden", "role", "focusable", "data-slot"}
MAX_SVG_BYTES = 100_000
MAX_SVG_ELEMENTS = 512
MAX_SVG_PATHS = 256


class IconLibraryError(ValueError):
    pass


def _identity(library: str, name: str, style: str) -> tuple[str, str, str]:
    if library not in VERSIONS:
        raise IconLibraryError(f"Unsupported icon library: {library!r}")
    if style not in STYLES[library]:
        raise IconLibraryError(f"Unsupported {library} style: {style}")
    valid_name = (MATERIAL_NAME_PATTERN.fullmatch(name)
                  if library == "material_symbols" and isinstance(name, str)
                  else NAME_PATTERN.fullmatch(name) if isinstance(name, str) else None)
    if not valid_name or len(name) > 100:
        description = ("web/<lowercase_symbol_name> using underscores"
                       if library == "material_symbols" else "a lower-case kebab-case slug")
        raise IconLibraryError(f"Icon name must be {description}")
    if ((library == "tabler" and name.startswith("brand-"))
            or (library in ("phosphor", "material_symbols") and "logo" in name)):
        raise IconLibraryError(
            "Brand-logo glyphs require item-level license/trademark review and are disabled by default")
    return library, name, style


def suggest_icons(query: str, *, libraries: tuple[str, ...] | None = None,
                  limit: int = 3) -> list[dict]:
    """Return 0–3 deterministic, explainable semantic suggestions; never fetches.

    Only a small reviewed role/alias vocabulary is accepted. The result is a
    candidate list, not a claim that an icon is right for a brand or licensed
    for every trademark context.
    """
    if not isinstance(query, str) or not query.strip():
        raise IconLibraryError("Icon suggestion query must be non-empty text")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 3:
        raise IconLibraryError("Icon suggestion limit must be an integer from 0 to 3")
    role = query.strip().lower()
    role = SEMANTIC_ALIASES.get(role, role)
    if role not in SEMANTIC_ROLES or limit == 0:
        return []
    selected = tuple(DEFAULT_STYLES) if libraries is None else libraries
    if not isinstance(selected, tuple) or any(pack not in VERSIONS for pack in selected):
        raise IconLibraryError("libraries must be a tuple of supported icon pack IDs")
    suggestions = []
    for library in dict.fromkeys(selected):
        name = SEMANTIC_ICONS[library].get(role)
        if name is None:
            continue
        suggestions.append({
            "role": role,
            "library": library,
            "name": name,
            "style": DEFAULT_STYLES[library],
            "version": VERSIONS[library],
            "license": dict(LICENSES[library]),
            "rationale": f"The explicit semantic role {role!r} has a curated symbol in {library}.",
            "rights_status": "unknown",
        })
        if len(suggestions) == limit:
            break
    return suggestions


def _url(library: str, name: str, style: str, *, weight: int = 400,
         fill: bool = False, grade: int = 0, optical_size: int = 24) -> str:
    if library == "lucide":
        return ("https://raw.githubusercontent.com/lucide-icons/lucide/"
                f"{VERSIONS[library]}/icons/{name}.svg")
    if library == "heroicons":
        return ("https://raw.githubusercontent.com/tailwindlabs/heroicons/"
                f"{VERSIONS[library]}/optimized/24/{style}/{name}.svg")
    if library == "tabler":
        directory = "outline" if style == "outline" else "filled"
        return ("https://raw.githubusercontent.com/tabler/tabler-icons/"
                f"{VERSIONS[library]}/icons/{directory}/{name}.svg")
    if library == "phosphor":
        suffix = "" if style == "regular" else f"-{style}"
        return ("https://raw.githubusercontent.com/phosphor-icons/core/"
                f"{VERSIONS[library]}/assets/{style}/{name}{suffix}.svg")
    symbol = name.split("/", 1)[1]
    variant = "" if weight == 400 else f"wght{weight}"
    if grade:
        variant += ("gradN25" if grade == -25 else "grad200")
    if fill:
        variant += "fill1"
    variant = f"_{variant}" if variant else ""
    return ("https://raw.githubusercontent.com/google/material-design-icons/"
            f"{VERSIONS[library]}/symbols/web/{symbol}/materialsymbols{style}/"
            f"{symbol}{variant}_{optical_size}px.svg")


def _material_variant(weight: int, fill: bool, grade: int, optical_size: int) -> None:
    if type(weight) is not int or weight not in (100, 200, 300, 400, 500, 600, 700):
        raise IconLibraryError("Material Symbols weight must be one of 100, 200, 300, 400, 500, 600, 700")
    if not isinstance(fill, bool):
        raise IconLibraryError("Material Symbols fill must be a boolean")
    if type(grade) is not int or grade not in (-25, 0, 200):
        raise IconLibraryError("Material Symbols grade must be -25, 0, or 200")
    if type(optical_size) is not int or optical_size not in (20, 24, 40, 48):
        raise IconLibraryError("Material Symbols optical_size must be 20, 24, 40, or 48")


def _validated(svg_bytes: bytes) -> ET.Element:
    if len(svg_bytes) > MAX_SVG_BYTES:
        raise IconLibraryError("SVG exceeds 100KB safety limit")
    lowered = svg_bytes.lower()
    if any(token in lowered for token in (b"<!doctype", b"<!entity",
                                           b"<?xml-stylesheet", b"<script",
                                           b"<style", b"data:", b"url(")):
        raise IconLibraryError("SVG contains unsupported or unsafe content")
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        raise IconLibraryError("Malformed SVG") from exc
    if root.tag != SVG + "svg":
        raise IconLibraryError("Only SVG icon documents are accepted")
    nodes = list(root.iter())
    if len(nodes) > MAX_SVG_ELEMENTS:
        raise IconLibraryError(f"SVG exceeds {MAX_SVG_ELEMENTS} element safety limit")
    if sum(node.tag == SVG + "path" for node in nodes) > MAX_SVG_PATHS:
        raise IconLibraryError(f"SVG exceeds {MAX_SVG_PATHS} path safety limit")
    for node in nodes:
        tag = node.tag.split("}")[-1]
        if tag not in ALLOWED_TAGS:
            raise IconLibraryError(f"Unsupported SVG element: {tag}")
        for key, val in node.attrib.items():
            clean_key = key.split("}")[-1]
            if clean_key not in ALLOWED_ATTRS or "}" in key and not key.startswith("{http://www.w3.org/2000/svg}"):
                raise IconLibraryError(f"Unsupported SVG attribute: {key}")
            if "http:" in val or "https:" in val or "javascript:" in val or "url(" in val:
                raise IconLibraryError("SVG has external or executable reference")
    return root


def asset(library: str, name: str, *, style: str | None = None,
          cache_dir: str | Path | None = None, offline: bool = False,
          weight: int = 400, fill: bool = False, grade: int = 0,
          optical_size: int = 24) -> Path:
    if library not in DEFAULT_STYLES:
        raise IconLibraryError(f"Unsupported icon library: {library!r}")
    library, name, style = _identity(
        library, name, DEFAULT_STYLES[library] if style is None else style)
    if library == "material_symbols":
        _material_variant(weight, fill, grade, optical_size)
    elif (weight, fill, grade, optical_size) != (400, False, 0, 24):
        raise IconLibraryError("weight/fill/grade/optical_size are only supported by Material Symbols")
    base = (Path(cache_dir) if cache_dir is not None
            else Path.home() / ".cache" / "reels-maker" / "icon-libraries")
    cache_name = name.replace("/", "--")
    if library == "material_symbols":
        variant = "" if weight == 400 else f"-w{weight}"
        variant += f"-f{int(fill)}-g{grade}-o{optical_size}"
        cache_name += variant
    target = base / library / VERSIONS[library] / style / f"{cache_name}.svg"
    if target.exists():
        _validated(target.read_bytes())
        return target
    if offline:
        raise IconLibraryError(
            f"Icon {library}/{name} not cached; provision it before offline render")
    try:
        request = urllib.request.Request(
            _url(library, name, style, weight=weight, fill=fill,
                 grade=grade, optical_size=optical_size),
            headers={"User-Agent": "reels-maker-icon-library/1"})
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(MAX_SVG_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise IconLibraryError(
            f"Cannot fetch {library}/{name}; cache icons before rendering offline") from exc
    _validated(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".svg.tmp")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return target


def _homebrew_cairo_fallback() -> None:
    """Let dyld find Homebrew libcairo without overriding other libraries.

    cairocffi/dlopen does not search /opt/homebrew/lib on macOS. Appending it
    to DYLD_FALLBACK_LIBRARY_PATH (lazy-read at dlopen time) only supplies
    libraries nothing else resolved — Pillow's bundled font libraries are
    never substituted, unlike a broad DYLD_LIBRARY_PATH export.
    """
    if sys.platform != "darwin":
        return
    prefix = "/opt/homebrew/lib"
    if not Path(prefix, "libcairo.2.dylib").is_file():
        return
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH")
    if not existing:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = prefix
    elif prefix not in existing.split(":"):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{existing}:{prefix}"


@lru_cache(maxsize=512)
def _raster(cache_path: str, colour: str, size: int, stroke_width: float) -> Image.Image:
    _homebrew_cairo_fallback()
    try:
        import cairosvg
    except (ImportError, OSError) as exc:
        raise IconLibraryError(
            'SVG icons require pip install -e ".[icons]" and system cairo '
            "(brew install cairo)") from exc
    svg = Path(cache_path).read_bytes()
    root = _validated(svg)
    if not HEX_PATTERN.fullmatch(colour):
        raise IconLibraryError("Icon colour must be #RRGGBB")
    for node in root.iter():
        for key in ("fill", "stroke"):
            value = node.get(key)
            if value == "currentColor" or (
                    value is not None and value.lower() not in ("none", "transparent")
                    and key == "fill" and node.get("fill") != "none"):
                node.set(key, colour)
        if stroke_width > 0 and "stroke-width" in node.attrib:
            node.set("stroke-width", str(stroke_width))
    # Filled-icon packs (Material Symbols, solid variants) ship paths without a
    # fill attribute; an unset fill inherits black, so inject the brand colour
    # at the root. Packs whose root is explicitly fill="none" (stroke-based)
    # must stay unfilled or every glyph becomes a solid blob.
    if (root.get("fill") or "").lower() not in ("none", "transparent"):
        root.set("fill", colour)
    root.set("color", colour)
    png = cairosvg.svg2png(
        bytestring=ET.tostring(root, encoding="utf-8"),
        output_width=size, output_height=size)
    return Image.open(BytesIO(png)).convert("RGBA")


def raster(library: str, name: str, size: int, colour: str,
           *, style: str | None = None, stroke_width: float = 0,
           cache_dir: str | Path | None = None,
           offline: bool = False, weight: int = 400, fill: bool = False,
           grade: int = 0, optical_size: int = 24) -> Image.Image:
    if not 4 <= size <= 4096:
        raise IconLibraryError("Icon size must be between 4 and 4096 pixels")
    if not HEX_PATTERN.fullmatch(colour):
        raise IconLibraryError("Icon colour must be #RRGGBB")
    if not 0 <= stroke_width <= 12:
        raise IconLibraryError("Icon stroke width must be 0–12")
    path = asset(library, name, style=style, cache_dir=cache_dir,
                 offline=offline, weight=weight, fill=fill, grade=grade,
                 optical_size=optical_size)
    return _raster(str(path), colour.upper(), int(size), float(stroke_width)).copy()


def provenance(library: str, name: str, *, style: str | None = None,
               cache_dir: str | Path | None = None, offline: bool = False,
               weight: int = 400, fill: bool = False, grade: int = 0,
               optical_size: int = 24) -> dict:
    """Return deterministic source/license/checksum evidence for an icon use."""
    path = asset(library, name, style=style, cache_dir=cache_dir,
                 offline=offline, weight=weight, fill=fill, grade=grade,
                 optical_size=optical_size)
    library, name, resolved_style = _identity(
        library, name, DEFAULT_STYLES[library] if style is None else style)
    return {
        "provider": library,
        "asset_id": name,
        "version": VERSIONS[library],
        "style": resolved_style,
        "license": dict(LICENSES[library]),
        "source_url": _url(library, name, resolved_style, weight=weight,
                           fill=fill, grade=grade, optical_size=optical_size),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rights_status": "unknown",
        "note": "Pack license recorded; trademark/brand and item-level use still require review.",
    }
