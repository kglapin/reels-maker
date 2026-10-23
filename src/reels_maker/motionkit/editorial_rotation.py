"""Opt-in editorial frame and typography rotation for the scene graph."""
from __future__ import annotations
import math
from typing import Mapping
from ..core.scene_graph import Node
from .keyframes import Track

FAMILIES = ("tilt-settle", "counter-rotation", "diagonal-hold", "rotation-to-layout")

def _number(value, field, lower, upper):
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"{field} must be between {lower} and {upper}")
    return result

def rotation_track(spec: Mapping, duration: float, *, role: str) -> Track:
    if not isinstance(spec, Mapping):
        raise ValueError("rotation spec must be a mapping")
    family = str(spec.get("family", "tilt-settle"))
    if family not in FAMILIES:
        raise ValueError(f"Unknown rotation family: {family}")
    duration = _number(duration, "duration", .1, 300)
    peak = _number(spec.get("angle", -6 if role == "photo" else 4),
                   "angle", -35, 35)
    settle = _number(spec.get("settle_angle", 0), "settle_angle", -15, 15)
    start = _number(spec.get("start", .05), "start", 0, duration)
    travel = _number(spec.get("duration", min(.75, duration * .33)),
                     "rotation duration", .05, duration)
    end = min(duration, start + travel)
    if end <= start:
        raise ValueError("Rotation must have positive duration")
    easing = str(spec.get("easing", "out-cubic"))
    if family == "diagonal-hold":
        return Track.from_pairs([(0, peak), (start, peak),
                                 (end, settle)], easing=easing)
    if family == "rotation-to-layout":
        return Track.from_pairs([(0, settle), (start, settle),
                                 (end, peak)], easing=easing)
    return Track.from_pairs([(0, peak), (end, settle)], easing=easing)

def apply_editorial_rotations(elements: Mapping[str, Node],
                              settings: Mapping, duration: float) -> list[dict]:
    """Attach rotation to named roles without overwriting other tracks."""
    if not isinstance(settings, Mapping):
        raise ValueError("editorial_rotation must be an object keyed by role")
    warnings = []
    for role, spec in settings.items():
        if role not in elements:
            warnings.append({"code":"rotation_missing_role","role":role,
                             "message":"Rotation references a missing scene element"})
            continue
        node = elements[role]
        if "rotation" in node.tracks and not spec.get("override", False):
            warnings.append({"code":"rotation_existing_track","role":role,
                             "message":"Existing authored rotation preserved"})
            continue
        node.track("rotation", rotation_track(spec, duration, role=role))
        node.meta["editorial_rotation"] = {
            "family":spec.get("family","tilt-settle"),
            "reason":spec.get("reason","explicit art direction")}
    return warnings

def editorial_media_nodes(scene: Mapping, width: int, height: int,
                          duration: float) -> list[Node]:
    """Generate image windows with independent rotation, in normalized units."""
    items = scene.get("editorial_media") or []
    if not isinstance(items, list):
        raise ValueError("editorial_media must be a list")
    result = []
    for idx, item in enumerate(items):
        if not isinstance(item, Mapping) or not item.get("asset"):
            raise ValueError("editorial_media items require asset paths")
        x = _number(item.get("x", 0), "x", 0, 1)
        y = _number(item.get("y", 0), "y", 0, 1)
        w = _number(item.get("w", 1), "w", .02, 1)
        h = _number(item.get("h", 1), "h", .02, 1)
        if x+w > 1.001 or y+h > 1.001:
            raise ValueError("editorial_media rectangle must fit within canvas")
        node = Node(kind="image", role=f"editorial-photo-{idx}",
                    qa_class="visual",
                    props={"path":str(item["asset"]),
                           "x":width*x,"y":height*y,
                           "w":width*w,"h":height*h,
                           "zoom":_number(item.get("zoom",1.0),"zoom",1,1.4)})
        if "rotation" in item:
            spec=item["rotation"]
            node.track("rotation",rotation_track(spec,duration,role="photo"))
            node.meta["editorial_rotation"]={"family":spec.get("family","tilt-settle")}
        result.append(node)
    return result
