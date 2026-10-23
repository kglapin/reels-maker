"""Version-pinned Lucide and Heroicons SVG assets for the native renderer.

Icons are downloaded only on a cache miss; subsequent renders use on-disk
copies, never hotlinked graphics. Names are strict slugs (no path traversal).
The source SVG is vetted before passing it to CairoSVG: no scripts, external
references, embedded images, CSS or XML entity declarations.
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image

VERSIONS = {"lucide": "0.468.0", "heroicons": "v2.2.0"}
STYLES = {"lucide": ("outline",), "heroicons": ("outline", "solid")}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
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
                 "stroke-opacity", "aria-hidden", "role", "focusable"}
MAX_SVG_BYTES = 100_000


class IconLibraryError(ValueError):
    pass


def _identity(library: str, name: str, style: str) -> tuple[str, str, str]:
    if library not in VERSIONS:
        raise IconLibraryError("Icon library must be lucide or heroicons")
    if style not in STYLES[library]:
        raise IconLibraryError(f"Unsupported {library} style: {style}")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name) or len(name) > 80:
        raise IconLibraryError("Icon name must be a lower-case kebab-case slug")
    return library, name, style


def _url(library: str, name: str, style: str) -> str:
    if library == "lucide":
        return ("https://raw.githubusercontent.com/lucide-icons/lucide/"
                f"{VERSIONS[library]}/icons/{name}.svg")
    return ("https://raw.githubusercontent.com/tailwindlabs/heroicons/"
            f"{VERSIONS[library]}/optimized/24/{style}/{name}.svg")


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
    for node in root.iter():
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


def asset(library: str, name: str, *, style: str = "outline",
          cache_dir: str | Path | None = None, offline: bool = False) -> Path:
    library, name, style = _identity(library, name, style)
    base = (Path(cache_dir) if cache_dir is not None
            else Path.home() / ".cache" / "reels-maker" / "icon-libraries")
    target = base / library / VERSIONS[library] / style / f"{name}.svg"
    if target.exists():
        _validated(target.read_bytes())
        return target
    if offline:
        raise IconLibraryError(
            f"Icon {library}/{name} not cached; provision it before offline render")
    try:
        request = urllib.request.Request(
            _url(library, name, style),
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


@lru_cache(maxsize=512)
def _raster(cache_path: str, colour: str, size: int, stroke_width: float) -> Image.Image:
    try:
        import cairosvg
    except ImportError as exc:
        raise IconLibraryError(
            'SVG icons require pip install -e ".[icons]"') from exc
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
    root.set("color", colour)
    png = cairosvg.svg2png(
        bytestring=ET.tostring(root, encoding="utf-8"),
        output_width=size, output_height=size)
    return Image.open(BytesIO(png)).convert("RGBA")


def raster(library: str, name: str, size: int, colour: str,
           *, style: str = "outline", stroke_width: float = 0,
           cache_dir: str | Path | None = None,
           offline: bool = False) -> Image.Image:
    if not 4 <= size <= 4096:
        raise IconLibraryError("Icon size must be between 4 and 4096 pixels")
    if not HEX_PATTERN.fullmatch(colour):
        raise IconLibraryError("Icon colour must be #RRGGBB")
    if not 0 <= stroke_width <= 12:
        raise IconLibraryError("Icon stroke width must be 0–12")
    path = asset(library, name, style=style, cache_dir=cache_dir,
                 offline=offline)
    return _raster(str(path), colour.upper(), int(size), float(stroke_width)).copy()
