"""Retained scene graph with animated, composable node properties.

The graph is deliberately renderer-agnostic. A node stores geometry in scene
pixels plus optional property tracks. Sampling at a timestamp returns a plain
resolved graph that a software renderer, a QA bounds checker or a preview tool
can consume without knowing how the animation was authored.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Mapping

if TYPE_CHECKING:
    from ..motionkit.keyframes import Track

BBox = tuple[float, float, float, float]


@dataclass
class Node:
    kind: str
    role: str = "decor"
    props: dict[str, Any] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    dx: float = 0.0
    dy: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    anchor: tuple[float, float] | None = None
    clip: BBox | None = None
    reveal: dict[str, Any] | None = None
    tracks: dict[str, "Track"] = field(default_factory=dict, repr=False)
    qa_class: str = "decor"
    meta: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ tracks
    def track(self, name: str, track: "Track") -> "Node":
        if not name:
            raise ValueError("Track name cannot be empty")
        self.tracks[name] = track
        return self

    def onset(self) -> float:
        if not self.tracks:
            return 0.0
        return min(track.start for track in self.tracks.values())

    def settle(self) -> float:
        if not self.tracks:
            return 0.0
        return max(track.end for track in self.tracks.values())

    def sample(self, time: float) -> "Node":
        if not math.isfinite(time):
            raise ValueError("Sample time must be finite")
        node = copy.copy(self)
        node.props = dict(self.props)
        node.children = [child.sample(time) for child in self.children]
        for name, track in self.tracks.items():
            value = track.value(time)
            if name == "opacity":
                node.opacity = max(0.0, min(1.0, float(value)))
            elif name == "scale":
                node.scale = float(value)
            elif name == "rotation":
                node.rotation = float(value)
            elif name == "dx":
                node.dx = float(value)
            elif name == "dy":
                node.dy = float(value)
            elif name == "reveal":
                node.reveal = {**(node.reveal or {}), "progress":
                               max(0.0, min(1.0, float(value)))}
            elif name.startswith("prop."):
                node.props[name[5:]] = value
            else:
                raise ValueError(f"Unknown animated property {name!r}")
        if node.reveal is not None:
            node.reveal = dict(node.reveal)
            if "progress" not in node.reveal:
                node.reveal["progress"] = 1.0
        return node

    # ------------------------------------------------------------------ bounds
    def base_bounds(self) -> BBox | None:
        props = self.props
        kind = self.kind
        if kind in ("rect", "round", "panel", "image", "block"):
            x, y = float(props.get("x", 0)), float(props.get("y", 0))
            w, h = float(props.get("w", 0)), float(props.get("h", 0))
            if w < 0 or h < 0:
                raise ValueError("Node width/height cannot be negative")
            return (x, y, x + w, y + h)
        if kind == "circle":
            cx, cy = float(props["cx"]), float(props["cy"])
            radius = float(props["r"])
            return (cx - radius, cy - radius, cx + radius, cy + radius)
        if kind == "ring":
            cx, cy = float(props["cx"]), float(props["cy"])
            radius = float(props["r"]) + float(props.get("width", 0)) / 2
            return (cx - radius, cy - radius, cx + radius, cy + radius)
        if kind == "line":
            x1, y1 = float(props["x1"]), float(props["y1"])
            x2, y2 = float(props["x2"]), float(props["y2"])
            stroke = float(props.get("width", 1)) / 2
            return (min(x1, x2) - stroke, min(y1, y2) - stroke,
                    max(x1, x2) + stroke, max(y1, y2) + stroke)
        if kind == "path":
            points = props.get("points") or []
            if not points:
                return None
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            stroke = float(props.get("width", 1)) / 2
            return (min(xs) - stroke, min(ys) - stroke,
                    max(xs) + stroke, max(ys) + stroke)
        if kind == "group" or kind == "scene":
            boxes = [child.world_bounds() for child in self.children]
            boxes = [box for box in boxes if box is not None]
            return union_boxes(boxes) if boxes else None
        if kind in ("text", "number"):
            x, y = float(props.get("x", 0)), float(props.get("y", 0))
            w, h = float(props.get("w", 0)), float(props.get("h", 0))
            return (x, y, x + w, y + h)
        raise ValueError(f"Unsupported node kind {self.kind!r}")

    def world_bounds(self) -> BBox | None:
        box = self.base_bounds()
        if box is None:
            return None
        x0, y0, x1, y1 = box
        anchor = self.anchor or ((x0 + x1) / 2, (y0 + y1) / 2)
        ax, ay = anchor
        if self.scale != 1:
            x0, x1 = ax + (x0 - ax) * self.scale, ax + (x1 - ax) * self.scale
            y0, y1 = ay + (y0 - ay) * self.scale, ay + (y1 - ay) * self.scale
        if self.rotation:
            angle = math.radians(self.rotation)
            cosine, sine = math.cos(angle), math.sin(angle)
            corners = []
            for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                rx = ax + (px - ax) * cosine - (py - ay) * sine
                ry = ay + (px - ax) * sine + (py - ay) * cosine
                corners.append((rx, ry))
            x0 = min(point[0] for point in corners)
            x1 = max(point[0] for point in corners)
            y0 = min(point[1] for point in corners)
            y1 = max(point[1] for point in corners)
        x0 += self.dx
        x1 += self.dx
        y0 += self.dy
        y1 += self.dy
        box = (x0, y0, x1, y1)
        if self.clip is not None:
            clipped = intersect_boxes(box, self.clip)
            box = clipped
        if self.reveal is not None and self.reveal.get("progress", 1) < 1:
            box = _reveal_bbox(box, self.reveal)
        return box

    def visible(self) -> bool:
        return self.opacity > .015

    def flatten(self) -> Iterable["Node"]:
        yield self
        for child in self.children:
            yield from child.flatten()


def union_boxes(boxes: Iterable[BBox]) -> BBox:
    boxes = list(boxes)
    if not boxes:
        raise ValueError("At least one box is required")
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def intersect_boxes(first: BBox, second: BBox) -> BBox:
    return (max(first[0], second[0]), max(first[1], second[1]),
            min(first[2], second[2]), min(first[3], second[3]))


def boxes_overlap(first: BBox, second: BBox, padding: float = 0.0) -> bool:
    return not (first[2] + padding <= second[0]
                or second[2] + padding <= first[0]
                or first[3] + padding <= second[1]
                or second[3] + padding <= first[1])


def overlap_area(first: BBox, second: BBox) -> float:
    width = min(first[2], second[2]) - max(first[0], second[0])
    height = min(first[3], second[3]) - max(first[1], second[1])
    return max(0.0, width) * max(0.0, height)


def _reveal_bbox(box: BBox, reveal: Mapping[str, Any]) -> BBox:
    progress = max(0.0, min(1.0, float(reveal.get("progress", 1))))
    direction = reveal.get("direction", "up")
    x0, y0, x1, y1 = box
    if direction in ("up", "left"):
        fraction = 1 - progress
    elif direction in ("down", "right"):
        fraction = progress
    else:
        raise ValueError("Reveal direction must be up, down, left or right")
    if direction in ("up", "down"):
        height = y1 - y0
        if direction == "up":
            return (x0, y1 - height * progress, x1, y1)
        return (x0, y0, x1, y0 + height * progress)
    width = x1 - x0
    if direction == "left":
        return (x1 - width * progress, y0, x1, y1)
    return (x0, y0, x0 + width * progress, y1)


def collect_qa_elements(root: Node) -> list[dict[str, Any]]:
    """Flatten visible text/control nodes into QA-friendly records."""
    result = []

    def transform(box: BBox, node: Node) -> BBox:
        x0, y0, x1, y1 = box
        base = node.base_bounds()
        anchor = node.anchor or (
            ((base[0] + base[2]) / 2, (base[1] + base[3]) / 2)
            if base is not None else ((x0 + x1) / 2, (y0 + y1) / 2))
        ax, ay = anchor
        if node.scale != 1:
            x0, x1 = ax + (x0 - ax) * node.scale, ax + (x1 - ax) * node.scale
            y0, y1 = ay + (y0 - ay) * node.scale, ay + (y1 - ay) * node.scale
        if node.rotation:
            angle = math.radians(node.rotation)
            cosine, sine = math.cos(angle), math.sin(angle)
            corners = []
            for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                corners.append((ax + (px - ax) * cosine - (py - ay) * sine,
                                ay + (px - ax) * sine + (py - ay) * cosine))
            x0, x1 = min(p[0] for p in corners), max(p[0] for p in corners)
            y0, y1 = min(p[1] for p in corners), max(p[1] for p in corners)
        return (x0 + node.dx, y0 + node.dy,
                x1 + node.dx, y1 + node.dy)

    def walk(node: Node, ancestors: tuple[Node, ...],
             parent_opacity: float) -> None:
        if not node.visible():
            return
        effective_opacity = parent_opacity * node.opacity
        if node.children:
            # A group is a transform/opacity container. Its own control class
            # is deliberately omitted; leaf text and controls are checked.
            for child in node.children:
                walk(child, ancestors + (node,), effective_opacity)
            return
        if node.qa_class not in ("text", "control"):
            return
        box = node.world_bounds()
        if box is not None and node.meta.get("bounds"):
            raw = node.meta["bounds"]
            box = (raw[0], raw[1], raw[2], raw[3])
            # Apply the leaf's actual transform, then the containing groups
            # from inner to outer, mirroring the renderer's nested layers.
            box = transform(box, node)
        if box is None:
            return
        for ancestor in reversed(ancestors):
            box = transform(box, ancestor)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        result.append({
            "role": node.role,
            "path": "/".join(
                [ancestor.role for ancestor in ancestors
                 if ancestor.role != "decor"] + [node.role]),
            "class": node.qa_class,
            "bounds": tuple(round(value, 2) for value in box),
            "opacity": round(effective_opacity, 4),
            "meta": dict(node.meta),
        })

    walk(root, (), 1.0)
    return result
