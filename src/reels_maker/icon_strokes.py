"""Trace stroke-based icon SVGs into polylines for draw-on animation.

Lucide-style packs ship ``fill="none"`` stroke glyphs built from ``path``,
``circle``, ``ellipse``, ``rect``, ``line``, ``polyline`` and ``polygon``
elements. Flattening those shapes into point lists lets the scene renderer
draw each stroke progressively through the existing ``path`` node ``progress``
trim, producing a genuine "icon is being drawn" entrance instead of a raster
pop. Filled glyph packs (Material Symbols) return ``None`` so callers can
fall back to the cached raster icon.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .icon_library import SVG as SVG_NS, asset

_NUMBER = re.compile(
    r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_COMMANDS = set("MmLlHhVvCcSsQqTtAaZz")
# Flattening density: enough segments that a ~100 px icon reads as smooth ink.
_CURVE_STEPS = 20
_ARC_STEPS = 32


class StrokeTraceError(ValueError):
    """The SVG cannot be represented as stroke polylines."""


@dataclass(frozen=True)
class Stroke:
    points: tuple[tuple[float, float], ...]
    closed: bool = False
    width: float = 1.0


@dataclass(frozen=True)
class StrokeIcon:
    view_box: tuple[float, float, float, float]
    strokes: tuple[Stroke, ...] = field(default_factory=tuple)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _number_stream(data: str) -> list[float]:
    return [float(match.group(0)) for match in _NUMBER.finditer(data)]


def _path_commands(data: str) -> list[tuple[str, list[float]]]:
    """Split an SVG ``d`` attribute into (command, args) pairs."""
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
                        data)
    commands: list[tuple[str, list[float]]] = []
    index = 0
    current: str | None = None
    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            if token not in _COMMANDS:
                raise StrokeTraceError(f"Unsupported path command {token!r}")
            current = token
            index += 1
            if current in "Zz":
                commands.append((current, []))
                continue
        elif current is None:
            raise StrokeTraceError("Path data must start with a command")
        else:
            index += 0  # repeat of the previous command consumes numbers below
        if current is None or current in "Zz":
            continue
        arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4,
                 "T": 2, "A": 7}.get(current.upper(), 0)
        if arity == 0:
            raise StrokeTraceError(f"Path command {current!r} needs arguments")
        args: list[float] = []
        while index < len(tokens) and not tokens[index].isalpha():
            args.append(float(tokens[index]))
            index += 1
        if len(args) % arity:
            raise StrokeTraceError(
                f"Path command {current!r} has {len(args)} args, "
                f"expected a multiple of {arity}")
        for offset in range(0, len(args), arity):
            commands.append((current, args[offset:offset + arity]))
            if current in "Mm":
                current = "l" if current == "m" else "L"
    return commands


def _cubic(p0, p1, p2, p3, steps: int = _CURVE_STEPS):
    for step in range(1, steps + 1):
        t = step / steps
        u = 1.0 - t
        x = (u ** 3 * p0[0] + 3 * u * u * t * p1[0]
             + 3 * u * t * t * p2[0] + t ** 3 * p3[0])
        y = (u ** 3 * p0[1] + 3 * u * u * t * p1[1]
             + 3 * u * t * t * p2[1] + t ** 3 * p3[1])
        yield (x, y)


def _quadratic(p0, p1, p2, steps: int = _CURVE_STEPS):
    for step in range(1, steps + 1):
        t = step / steps
        u = 1.0 - t
        x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        yield (x, y)


def _arc_points(p0, radii, rotation, large_arc, sweep, p1):
    """SVG endpoint-to-center arc conversion, sampled to polyline points."""
    rx, ry = abs(radii[0]), abs(radii[1])
    if rx < 1e-9 or ry < 1e-9:
        return [p1]
    phi = math.radians(rotation % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx = (p0[0] - p1[0]) / 2.0
    dy = (p0[1] - p1[1]) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    sign = -1.0 if large_arc == sweep else 1.0
    num = (rx * rx * ry * ry - rx * rx * y1p * y1p
           - ry * ry * x1p * x1p)
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = sign * math.sqrt(max(0.0, num / den)) if den > 0 else 0.0
    cxp = coef * rx * y1p / ry
    cyp = -coef * ry * x1p / rx
    cx = cos_phi * cxp - sin_phi * cyp + (p0[0] + p1[0]) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (p0[1] + p1[1]) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        value = max(-1.0, min(1.0, dot / length)) if length else 1.0
        result = math.acos(value)
        if ux * vy - uy * vx < 0:
            result = -result
        return result

    theta1 = angle(1.0, 0.0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                  (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi
    points = []
    for step in range(1, _ARC_STEPS + 1):
        theta = theta1 + delta * step / _ARC_STEPS
        x = rx * math.cos(theta)
        y = ry * math.sin(theta)
        points.append((cx + cos_phi * x - sin_phi * y,
                       cy + sin_phi * x + cos_phi * y))
    return points


def _trace_path(data: str, width: float) -> list[Stroke]:
    commands = _path_commands(data)
    strokes: list[Stroke] = []
    current = (0.0, 0.0)
    subpath_start = current
    points: list[tuple[float, float]] = []
    last_control: tuple[float, float] | None = None
    last_quad: tuple[float, float] | None = None

    def flush(closed: bool = False) -> None:
        nonlocal points
        if len(points) >= 2:
            strokes.append(Stroke(tuple(points), closed=closed, width=width))
        points = []

    for command, args in commands:
        upper = command.upper()
        relative = command.islower()
        if upper == "M":
            flush()
            first = True
            for offset in range(0, len(args), 2):
                x, y = args[offset], args[offset + 1]
                if relative:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                if first:
                    subpath_start = current
                    points = [current]
                    first = False
                else:
                    # Subsequent coordinate pairs are implicit LineTos.
                    points.append(current)
            last_control = last_quad = None
            continue
        if upper == "L":
            for offset in range(0, len(args), 2):
                x, y = args[offset], args[offset + 1]
                if relative:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                points.append(current)
            last_control = last_quad = None
        elif upper == "H":
            for value in args:
                x = value + current[0] if relative else value
                current = (x, current[1])
                points.append(current)
            last_control = last_quad = None
        elif upper == "V":
            for value in args:
                y = value + current[1] if relative else value
                current = (current[0], y)
                points.append(current)
            last_control = last_quad = None
        elif upper == "C":
            for offset in range(0, len(args), 6):
                c1 = args[offset:offset + 2]
                c2 = args[offset + 2:offset + 4]
                end = args[offset + 4:offset + 6]
                if relative:
                    c1 = [c1[0] + current[0], c1[1] + current[1]]
                    c2 = [c2[0] + current[0], c2[1] + current[1]]
                    end = [end[0] + current[0], end[1] + current[1]]
                p0, p1, p2 = current, tuple(c1), tuple(c2)
                current = tuple(end)
                points.extend(_cubic(p0, p1, p2, current))
                last_control = p2
                last_quad = None
        elif upper == "S":
            for offset in range(0, len(args), 4):
                c2 = args[offset:offset + 2]
                end = args[offset + 2:offset + 4]
                if relative:
                    c2 = [c2[0] + current[0], c2[1] + current[1]]
                    end = [end[0] + current[0], end[1] + current[1]]
                p0 = current
                p1 = ((2 * current[0] - last_control[0],
                       2 * current[1] - last_control[1])
                      if last_control is not None else current)
                p2, current = tuple(c2), tuple(end)
                points.extend(_cubic(p0, p1, p2, current))
                last_control = p2
                last_quad = None
        elif upper == "Q":
            for offset in range(0, len(args), 4):
                ctrl = args[offset:offset + 2]
                end = args[offset + 2:offset + 4]
                if relative:
                    ctrl = [ctrl[0] + current[0], ctrl[1] + current[1]]
                    end = [end[0] + current[0], end[1] + current[1]]
                p0 = points[-1] if points else current
                ctrl_t, current = tuple(ctrl), tuple(end)
                points.extend(_quadratic(p0, ctrl_t, current))
                last_quad = ctrl_t
                last_control = None
        elif upper == "T":
            for offset in range(0, len(args), 2):
                end = args[offset:offset + 2]
                if relative:
                    end = [end[0] + current[0], end[1] + current[1]]
                p0 = points[-1] if points else current
                ctrl = ((2 * p0[0] - last_quad[0], 2 * p0[1] - last_quad[1])
                        if last_quad is not None else p0)
                current = tuple(end)
                points.extend(_quadratic(p0, ctrl, current))
                last_quad = ctrl
                last_control = None
        elif upper == "A":
            for offset in range(0, len(args), 7):
                rx, ry, rot = args[offset], args[offset + 1], args[offset + 2]
                large_arc, sweep = int(args[offset + 3]), int(args[offset + 4])
                end = args[offset + 5:offset + 7]
                if relative:
                    end = [end[0] + current[0], end[1] + current[1]]
                p0 = points[-1] if points else current
                current = tuple(end)
                points.extend(_arc_points(p0, (rx, ry), rot,
                                          large_arc, sweep, current))
                last_control = last_quad = None
        elif upper == "Z":
            current = subpath_start
            points.append(current)
            flush(closed=True)
            subpath_start = current
            last_control = last_quad = None
    flush()
    return strokes


def _trace_shape(element: ET.Element, width: float) -> list[Stroke]:
    tag = _local(element.tag)
    transform = element.get("transform")
    if transform:
        raise StrokeTraceError("Element transforms are not supported")
    if tag == "path":
        return _trace_path(element.get("d", ""), width)
    if tag in ("polyline", "polygon"):
        values = _number_stream(element.get("points", ""))
        points = [(values[i], values[i + 1])
                  for i in range(0, len(values) - 1, 2)]
        if len(points) < 2:
            return []
        return [Stroke(tuple(points), closed=tag == "polygon", width=width)]
    if tag == "line":
        return [Stroke(((float(element.get("x1", 0)),
                          float(element.get("y1", 0))),
                         (float(element.get("x2", 0)),
                          float(element.get("y2", 0)))),
                        width=width)]
    if tag in ("circle", "ellipse"):
        if tag == "circle":
            cx, cy = float(element.get("cx", 0)), float(element.get("cy", 0))
            rx = ry = float(element.get("r", 0))
        else:
            cx, cy = float(element.get("cx", 0)), float(element.get("cy", 0))
            rx, ry = float(element.get("rx", 0)), float(element.get("ry", 0))
        if rx <= 0 or ry <= 0:
            return []
        points = [(cx + rx * math.cos(2 * math.pi * i / _ARC_STEPS),
                   cy + ry * math.sin(2 * math.pi * i / _ARC_STEPS))
                  for i in range(_ARC_STEPS)]
        points.append(points[0])
        return [Stroke(tuple(points), closed=True, width=width)]
    if tag == "rect":
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        w, h = float(element.get("width", 0)), float(element.get("height", 0))
        if w <= 0 or h <= 0:
            return []
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        return [Stroke(tuple(points), closed=True, width=width)]
    raise StrokeTraceError(f"Unsupported icon element <{tag}>")


def trace_icon(library: str, name: str, *, style: str | None = None,
               cache_dir=None, offline: bool = False,
               weight: int = 400, fill: bool = False, grade: int = 0,
               optical_size: int = 24) -> StrokeIcon | None:
    """Return stroke polylines for a stroke-based icon, or ``None``.

    Returns ``None`` for filled glyph packs and for SVGs containing paint we
    cannot reproduce with stroked polylines, so callers can fall back to the
    raster icon without special-casing.
    """
    path = asset(library, name, style=style, cache_dir=cache_dir,
                 offline=offline, weight=weight, fill=fill, grade=grade,
                 optical_size=optical_size)
    try:
        root = ET.fromstring(path.read_bytes())
    except ET.ParseError as exc:
        raise StrokeTraceError("Cached icon SVG is not parseable") from exc
    view_box = root.get("viewBox")
    if view_box:
        parts = [float(part) for part in re.split(r"[\s,]+", view_box.strip())]
        if len(parts) != 4:
            raise StrokeTraceError("Icon viewBox must have four numbers")
        box = tuple(parts)
    else:
        box = (0.0, 0.0, float(root.get("width", 24)),
               float(root.get("height", 24)))
    strokes: list[Stroke] = []
    for element in root.iter():
        if element is root:
            continue
        tag = _local(element.tag)
        if tag in ("title", "desc", "metadata", "defs"):
            continue
        fill_value = (element.get("fill")
                      or root.get("fill") or "none")
        if fill_value not in ("none", "transparent"):
            return None
        opacity = element.get("opacity", root.get("opacity", "1"))
        try:
            if float(opacity) <= 0.01:
                continue
        except ValueError:
            return None
        stroke_width = element.get("stroke-width", root.get("stroke-width", "1"))
        try:
            width = float(stroke_width)
        except ValueError:
            return None
        strokes.extend(_trace_shape(element, width))
    if not strokes:
        return None
    return StrokeIcon(box, tuple(strokes))
