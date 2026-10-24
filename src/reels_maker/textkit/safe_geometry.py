"""Fail-closed ink-bounds checks for typeset text and safe-area polygons.

This is an additive geometry primitive, not a renderer integration. Coverage is
based on per-word FreeType ink bounding boxes, not glyph-outline intersection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from PIL import ImageFont

from reels_maker.core.transforms import Affine2D, Point
from .typesetter import FontBook, TextBlock, Word


_EPSILON = 1e-9
_MAX_TRANSFORM_COEFFICIENT = 1_000_000.0


@dataclass(frozen=True)
class InkBounds:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Ink bounds must be finite")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("Ink bounds must have positive area")

    @property
    def corners(self) -> tuple[Point, Point, Point, Point]:
        return (Point(self.left, self.top), Point(self.right, self.top),
                Point(self.right, self.bottom), Point(self.left, self.bottom))


@dataclass(frozen=True)
class SafePolygon:
    """A validated simple polygon in the coordinate space being checked."""

    vertices: tuple[tuple[float, float], ...]
    name: str = "safe-area"

    def __post_init__(self) -> None:
        vertices = tuple((float(x), float(y)) for x, y in self.vertices)
        object.__setattr__(self, "vertices", vertices)
        if len(vertices) < 3:
            raise ValueError("A safe polygon needs at least three vertices")
        if not self.name:
            raise ValueError("Polygon name cannot be empty")
        if any(not math.isfinite(value) for point in vertices for value in point):
            raise ValueError("Polygon coordinates must be finite")
        if any(_same_point(vertices[i], vertices[(i + 1) % len(vertices)])
               for i in range(len(vertices))):
            raise ValueError("Polygon cannot contain zero-length edges")
        count = len(vertices)
        for i in range(count):
            a, b = vertices[i], vertices[(i + 1) % count]
            for j in range(i + 1, count):
                # Adjacent edges share a vertex by design.
                if j == i or j == (i + 1) % count or (j + 1) % count == i:
                    continue
                c, d = vertices[j], vertices[(j + 1) % count]
                if _segments_intersect(a, b, c, d):
                    raise ValueError("Polygon must be simple (non-self-intersecting)")
        area2 = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in
                    zip(vertices, vertices[1:] + vertices[:1]))
        if abs(area2) <= _EPSILON:
            raise ValueError("Polygon must have non-zero area")

    def contains_point(self, x: float, y: float) -> bool:
        """Return True when ``(x, y)`` lies inside or on the boundary of this polygon."""
        return _inside((float(x), float(y)), self)


@dataclass(frozen=True)
class WordInk:
    line_index: int
    word_index: int
    text: str
    bounds: InkBounds
    essential: bool = True


@dataclass(frozen=True)
class GeometryFailure:
    line_index: int
    word_index: int
    text: str
    reason: str
    polygon_names: tuple[str, ...]


@dataclass(frozen=True)
class SafeGeometryReport:
    words: tuple[WordInk, ...]
    failures: tuple[GeometryFailure, ...]
    mask_boundary_failures: tuple[GeometryFailure, ...]

    @property
    def safe(self) -> bool:
        return not self.failures and not self.mask_boundary_failures


def _same_point(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= _EPSILON and abs(a[1] - b[1]) <= _EPSILON


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p) -> bool:
    return (min(a[0], b[0]) - _EPSILON <= p[0] <= max(a[0], b[0]) + _EPSILON
            and min(a[1], b[1]) - _EPSILON <= p[1] <= max(a[1], b[1]) + _EPSILON
            and abs(_orientation(a, b, p)) <= _EPSILON)


def _segments_intersect(a, b, c, d) -> bool:
    ab_c, ab_d = _orientation(a, b, c), _orientation(a, b, d)
    cd_a, cd_b = _orientation(c, d, a), _orientation(c, d, b)
    if ((ab_c > _EPSILON and ab_d < -_EPSILON or ab_c < -_EPSILON and ab_d > _EPSILON)
            and (cd_a > _EPSILON and cd_b < -_EPSILON or cd_a < -_EPSILON and cd_b > _EPSILON)):
        return True
    return ((_on_segment(a, b, c) or _on_segment(a, b, d)
             or _on_segment(c, d, a) or _on_segment(c, d, b)))


def _inside(point: tuple[float, float], polygon: SafePolygon) -> bool:
    """Boundary-inclusive point-in-polygon test."""
    x, y = point
    inside = False
    vertices = polygon.vertices
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if _on_segment(a, b, point):
            return True
        if (a[1] > y) != (b[1] > y):
            crossing_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < crossing_x:
                inside = not inside
    return inside


def _bounds_inside(bounds: InkBounds, polygon: SafePolygon) -> bool:
    corners = tuple((point.x, point.y) for point in bounds.corners)
    if not all(_inside(point, polygon) for point in corners):
        return False
    # For concave polygons, corners alone do not prove that bbox edges stay in.
    rect_edges = tuple(zip(corners, corners[1:] + corners[:1]))
    poly_edges = tuple(zip(polygon.vertices,
                           polygon.vertices[1:] + polygon.vertices[:1]))
    for edge in rect_edges:
        for boundary in poly_edges:
            if _segments_intersect(*edge, *boundary):
                # Coincident/touching boundaries are safe; proper crossings are not.
                if (_orientation(*edge, boundary[0]) * _orientation(*edge, boundary[1]) < -_EPSILON
                        and _orientation(*boundary, edge[0]) * _orientation(*boundary, edge[1]) < -_EPSILON):
                    return False
    return True


def _font_for(word: Word, fonts: FontBook, cache: dict,
              fallback_size: int) -> ImageFont.FreeTypeFont:
    path = word.font_path or fonts.path(word.weight)
    size = word.size or fallback_size
    if type(size) is not int or size < 6:
        raise ValueError(f"Invalid font size for word {word.text!r}")
    if not isinstance(word.font_index, int) or isinstance(word.font_index, bool) or word.font_index < 0:
        raise ValueError(f"Invalid font index for word {word.text!r}")
    key = (str(path), size, word.font_index)
    if key not in cache:
        cache[key] = ImageFont.truetype(str(path), size, index=word.font_index)
    return cache[key]


def _word_ink(word: Word, baseline: float, font: ImageFont.FreeTypeFont,
              transform: Affine2D | None) -> InkBounds:
    if not word.text or not math.isfinite(word.x) or not math.isfinite(baseline):
        raise ValueError(f"Missing or non-finite placement for word {word.text!r}")
    if not math.isfinite(word.tracking):
        raise ValueError(f"Non-finite tracking for word {word.text!r}")
    if transform is not None:
        values = (transform.a, transform.b, transform.c, transform.d,
                  transform.e, transform.f)
        if any(abs(value) > _MAX_TRANSFORM_COEFFICIENT for value in values):
            raise ValueError("Unsafe affine transform coefficient")
        determinant = transform.a * transform.d - transform.b * transform.c
        if not math.isfinite(determinant) or abs(determinant) <= _EPSILON:
            raise ValueError("Unsafe singular or near-singular affine transform")
    boxes = []
    for index, character in enumerate(word.text):
        if character.isspace():
            continue
        try:
            left, top, right, bottom = font.getbbox(character, anchor="ls")
            advance = float(font.getlength(word.text[:index])) + index * word.tracking
        except (AttributeError, OSError, ValueError) as exc:
            raise ValueError(f"Unable to measure FreeType ink for {word.text!r}") from exc
        values = (left, top, right, bottom, advance)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"Non-finite FreeType metrics for {word.text!r}")
        if right <= left or bottom <= top:
            raise ValueError(f"Empty FreeType ink metrics for {word.text!r}")
        glyph = InkBounds(word.x + advance + left, baseline + top,
                          word.x + advance + right, baseline + bottom)
        if transform is not None:
            corners = tuple(transform.apply(point) for point in glyph.corners)
            glyph = InkBounds(min(point.x for point in corners),
                              min(point.y for point in corners),
                              max(point.x for point in corners),
                              max(point.y for point in corners))
        boxes.append((glyph.left, glyph.top, glyph.right, glyph.bottom))
    if not boxes:
        raise ValueError(f"Empty FreeType ink metrics for {word.text!r}")
    bounds = InkBounds(min(box[0] for box in boxes), min(box[1] for box in boxes),
                       max(box[2] for box in boxes), max(box[3] for box in boxes))
    return bounds


def check_text_block(block: TextBlock, fonts: FontBook,
                     safe_polygons: Iterable[SafePolygon], *,
                     mask_polygons: Iterable[SafePolygon] = (),
                     transform: Affine2D | None = None) -> SafeGeometryReport:
    """Measure placed word ink and report safe-area and clipping failures.

    Every placed word is essential. A word must fit wholly inside one safe
    polygon and, when masks are supplied, wholly inside one visible mask polygon.
    A non-zero, invertible, bounded affine may map text and polygons together.
    """
    if not isinstance(block, TextBlock) or not isinstance(fonts, FontBook):
        raise TypeError("Expected a TextBlock and FontBook")
    if block.truncated:
        raise ValueError("Cannot certify a truncated TextBlock")
    safe = tuple(safe_polygons)
    masks = tuple(mask_polygons)
    if not safe:
        raise ValueError("At least one platform-safe polygon is required")
    if any(not isinstance(poly, SafePolygon) for poly in safe + masks):
        raise TypeError("All safe areas and masks must be SafePolygon instances")
    # Validate transform even for empty placement sets.
    if transform is not None:
        if not isinstance(transform, Affine2D):
            raise TypeError("transform must be an Affine2D")
        if any(abs(value) > _MAX_TRANSFORM_COEFFICIENT for value in
               (transform.a, transform.b, transform.c, transform.d, transform.e, transform.f)):
            raise ValueError("Unsafe affine transform coefficient")
        determinant = transform.a * transform.d - transform.b * transform.c
        if not math.isfinite(determinant) or abs(determinant) <= _EPSILON:
            raise ValueError("Unsafe singular or near-singular affine transform")
    placements = [(line_index, word_index, line.baseline, word)
                  for line_index, line in enumerate(block.lines)
                  for word_index, word in enumerate(line.words)]
    if not placements:
        raise ValueError("TextBlock has no measurable word placements")
    cache: dict = {}
    measured = tuple(WordInk(line_index, word_index, word.text,
                             _word_ink(word, float(baseline),
                                       _font_for(word, fonts, cache, block.style.size),
                                       transform))
                     for line_index, word_index, baseline, word in placements)
    failures = []
    mask_failures = []
    for item in measured:
        identity = (item.line_index, item.word_index, item.text)
        if not any(_bounds_inside(item.bounds, polygon) for polygon in safe):
            failures.append(GeometryFailure(*identity, "ink-bounds-outside-safe-polygon",
                                            tuple(poly.name for poly in safe)))
        if masks and not any(_bounds_inside(item.bounds, polygon) for polygon in masks):
            mask_failures.append(GeometryFailure(*identity, "ink-bounds-cross-mask-boundary",
                                                 tuple(poly.name for poly in masks)))
    return SafeGeometryReport(measured, tuple(failures), tuple(mask_failures))
