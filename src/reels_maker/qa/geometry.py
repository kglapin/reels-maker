"""Geometry checks for Studio QA."""
from __future__ import annotations

from copy import copy

from ..core.scene_graph import Node
from ..core.transforms import Affine2D, Space
from ..design.tokens import is_vertical_reels_canvas
from ..textkit.safe_geometry import InkBounds, SafePolygon, check_text_block
from ..textkit.typesetter import FontBook, TextBlock
from .models import Issue

SAFE_AREA_TOLERANCE = 1.5



def _safe_box(rect) -> tuple[float, float, float, float]:
    return (rect.x, rect.y, rect.right, rect.bottom)


def _inside_polygon(bounds: tuple[float, float, float, float],
                    polygon: SafePolygon) -> bool:
    """Check whether an entire axis-aligned visual bound fits in a safe zone."""
    try:
        rectangle = InkBounds(*bounds)
    except (TypeError, ValueError):
        # Invalid or degenerate visual bounds must fail closed in placement QA.
        return False
    return polygon.contains_bounds(rectangle)


def _overlaps(a, b, padding: float) -> bool:
    return not (a[2] + padding <= b[0] or b[2] + padding <= a[0]
                or a[3] + padding <= b[1] or b[3] + padding <= a[1])


def _overlap_area(a, b) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _text_blocks(root: Node) -> list[tuple[str, TextBlock]]:
    result = []
    for node in root.flatten():
        block = node.props.get("block")
        if isinstance(block, TextBlock):
            # Some metric compositions store their small semantic kicker in
            # the public `headline` element slot. Audit the declared typographic
            # role rather than misclassifying it as a display headline.
            role = str(node.meta.get("typography_role") or node.role)
            result.append((role, block))
    return result


def sample_geometry_frames(built, timing, fps: int,
                           samples_per_scene: int = 6) -> list[int]:
    """Combine evenly-spaced QA frames with track keys, easing extrema and probes.

    Every authored keyframe is mapped onto an output frame. Each interval
    between unique transform/property key times also gets quarter/mid/three-
    quarter probes plus exact analytical easing-extremum times (for overshoot
    curves such as ``back`` and ``spring``) so overshoots cannot hide between
    sparse samples. Sampling remains frame-quantized to inspect renderable times.
    """
    from ..motionkit.easing import easing_extrema_progress

    if type(samples_per_scene) is not int or samples_per_scene < 2:
        raise ValueError("samples_per_scene must be an integer >= 2")
    frames = timing.frames
    if type(frames) is not int or frames < 1 or type(fps) is not int or fps < 1:
        raise ValueError("QA frame count and FPS must be positive integers")
    indices = {round((frames - 1) * step / (samples_per_scene - 1))
               for step in range(samples_per_scene)}
    key_times = {0.0, max(0.0, (frames - 1) / fps)}
    extremum_times: set[float] = set()
    for root in built.nodes:
        for node in root.flatten():
            for track in node.tracks.values():
                key_times.update(float(key.time) for key in track.keys
                                 if 0 <= key.time <= built.duration)
                for left, right in zip(track.keys, track.keys[1:]):
                    span = float(right.time) - float(left.time)
                    if span <= 0:
                        continue
                    try:
                        extrema = easing_extrema_progress(right.easing)
                    except ValueError:
                        extrema = ()
                    for fraction in extrema:
                        t_ext = float(left.time) + span * fraction
                        if 0 <= t_ext <= built.duration:
                            extremum_times.add(t_ext)
    ordered = sorted(key_times)
    probes = set(ordered) | extremum_times
    for start, end in zip(ordered, ordered[1:]):
        span = end - start
        if span <= 0:
            continue
        probes.update(start + span * fraction for fraction in (.25, .5, .75))
    for time in probes:
        indices.add(max(0, min(frames - 1, round(time * fps))))
    return sorted(indices)


def _allowed_overlaps(project) -> set[frozenset[str]]:
    result = set()
    for scene in getattr(project, "scenes", []):
        if not isinstance(scene, dict):
            continue
        for pair in scene.get("allowed_overlaps", []) or []:
            if isinstance(pair, list) and len(pair) == 2:
                result.add(frozenset((str(pair[0]), str(pair[1]))))
    return result


def _collisions(elements: list[dict], allowed: set[frozenset[str]],
                built, time: float, local_frame: int) -> list[Issue]:
    issues = []
    threshold = 10.0
    for first in range(len(elements)):
        for second in range(first + 1, len(elements)):
            a, b = elements[first], elements[second]
            if a["opacity"] < .55 or b["opacity"] < .55:
                continue
            a_path, b_path = a.get("path", a["role"]), b.get("path", b["role"])
            if a_path == b_path:
                continue
            if (frozenset((a["role"], b["role"])) in allowed
                    or frozenset((a_path, b_path)) in allowed):
                continue
            if a["class"] == "decor" or b["class"] == "decor":
                continue
            if not _overlaps(a["bounds"], b["bounds"], -1.5):
                continue
            area = _overlap_area(a["bounds"], b["bounds"])
            if area < threshold:
                continue
            issues.append(Issue(
                "element_collision", "error",
                (f"Overlapping elements {a_path!r} and {b_path!r} "
                 f"({area:.0f}px²)."),
                built.index + 1, round(time, 3), [a_path, b_path],
                "Reduce type size, reflow copy or move the element to another region.",
                local_frame))
    return issues


def _safe_area(elements: list[dict], built, time: float,
               local_frame: int) -> list[Issue]:
    safe = _safe_box(built.layout.safe)
    issues = []
    tolerance = SAFE_AREA_TOLERANCE
    for element in elements:
        box = element["bounds"]
        if (box[0] < safe[0] - tolerance or box[1] < safe[1] - tolerance
                or box[2] > safe[2] + tolerance or box[3] > safe[3] + tolerance):
            issues.append(Issue(
                "safe_area_violation", "error",
                f"Element {element.get('path', element['role'])!r} leaves the safe rectangle.",
                built.index + 1, round(time, 3),
                [element.get("path", element["role"])],
                "Keep text and controls inside the platform-safe margins.",
                local_frame))
    return issues


def _vertical_reels_content_zone(built) -> list[Issue]:
    """Check authored copy/art placement in the 9:16 content zone.

    Geometry comes from the scene's authored layout transforms, before motion
    tracks are sampled. Background plates and the paths elements travel through
    therefore remain outside this placement rule.
    """
    from ..core.scene_graph import build_transform_hierarchy
    from ..core.transforms import Affine2D, Bounds, LocalSpace, Space
    from ..design.tokens import (
        is_vertical_reels_canvas, vertical_reels_content_polygon,
    )
    from ..textkit.typesetter import TextBlock

    width, height = built.context.width, built.context.height
    if not is_vertical_reels_canvas(width, height):
        return []
    zone = vertical_reels_content_polygon(width, height)

    def static_copy(node: Node) -> Node:
        """Flatten virtual journey page offsets; camera travel is motion."""
        result = copy(node)
        result.children = [static_copy(child) for child in node.children]
        if node.role.startswith("journey-step-"):
            result.dx = result.dy = 0.0
        return result

    roots = [static_copy(node) for node in built.nodes]
    root = Node(kind="group", role="reels-content-root", children=roots)
    hierarchy, transform_ids = build_transform_hierarchy(root)
    issues: list[Issue] = []

    def visit(node: Node, path: tuple[int, ...], ancestors: tuple[Node, ...],
              parent_path: tuple[str, ...]) -> None:
        role_path = parent_path + ((node.role,) if node.role != "decor" else ())
        label = "/".join(role_path) or node.role
        block = node.props.get("block")
        if isinstance(block, TextBlock) and not block.truncated:
            try:
                if "x" in node.props and "y" in node.props:
                    origin_x, origin_y = float(node.props["x"]), float(node.props["y"])
                else:
                    origin = node.meta.get("bounds")
                    if origin and len(origin) == 4:
                        origin_x, origin_y = float(origin[0]), float(origin[1])
                    else:
                        raise ValueError("missing text block scene origin")
                transform = Affine2D(e=origin_x, f=origin_y,
                                     source=Space.LOCAL, target=Space.LOCAL)
                for current in (node,) + tuple(reversed(ancestors)):
                    edge = current.local_to_parent_transform()
                    local_edge = Affine2D(
                        edge.a, edge.b, edge.c, edge.d, edge.e, edge.f,
                        Space.LOCAL, Space.LOCAL)
                    transform = transform.then(local_edge)
                report = check_text_block(
                    block, built.context.fonts, (zone,), transform=transform)
                if report.failures:
                    words = ", ".join(repr(item.text) for item in report.failures)
                    issues.append(Issue(
                        "reels_content_safe_zone", "error",
                        f"Text {label!r} extends into the vertical-Reels margin: {words}.",
                        built.index + 1, None, [label],
                        "Keep the authored text inside the content zone; animated travel is exempt."))
            except Exception as exc:
                issues.append(Issue(
                    "reels_content_safe_zone", "error",
                    f"Text {label!r} could not be checked against the vertical-Reels content zone: {exc}.",
                    built.index + 1, None, [label],
                    "Restore valid text metrics and keep the authored text inside the content zone."))

        asset_role = str(node.meta.get("asset_role", ""))
        is_asset_illustration = (
            node.kind in ("image", "video", "icon")
            and asset_role not in ("background", "marquee-photo")
            and not node.meta.get("background")
            and not any(token in node.role.lower()
                        for token in ("background", "backdrop"))
        )
        # Group bounds are only the union of their children; a wide chart or
        # marquee may deliberately include layout/loop padding. The actual
        # visible leaves and all text are checked below, so do not report the
        # non-rendering group envelope as an out-of-zone graphic.
        is_content_container = (
            node.qa_class in ("control", "visual")
            and node.kind not in ("group", "scene"))
        if is_asset_illustration or is_content_container:
            box = node.base_bounds()
            if box is not None:
                mapped = hierarchy.world_transform(
                    transform_ids[path]).map_bounds(Bounds[LocalSpace](*box))
                bounds = (mapped.left, mapped.top, mapped.right, mapped.bottom)
                if not _inside_polygon(bounds, zone):
                    issues.append(Issue(
                        "reels_content_safe_zone", "error",
                        f"Visual element {label!r} extends into the vertical-Reels margin.",
                        built.index + 1, None, [label],
                        "Keep the authored illustration inside the content zone; animated travel is exempt."))

        for index, child in enumerate(node.children):
            visit(child, path + (index,), ancestors + (node,), role_path)

    for index, child in enumerate(root.children):
        visit(child, (index,), (root,), ())
    return issues


def _text_ink_safe_area(roots: list[Node], built, time: float,
                        local_frame: int) -> list[Issue]:
    """Check placed FreeType word ink after the sampled scene-tree transforms."""
    safe_rect = built.layout.safe
    # Match the existing rectangular QA check's 1.5px raster-rounding tolerance.
    # This does not enlarge the authored safe area by a visual amount, but keeps
    # antialias/subpixel metrics consistent between the two geometry checks.
    tolerance = SAFE_AREA_TOLERANCE
    safe_polygon = SafePolygon(((safe_rect.x - tolerance, safe_rect.y - tolerance),
                                (safe_rect.right + tolerance, safe_rect.y - tolerance),
                                (safe_rect.right + tolerance, safe_rect.bottom + tolerance),
                                (safe_rect.x - tolerance, safe_rect.bottom + tolerance)),
                               "layout-safe")
    issues = []
    seen = set()

    def visit(node: Node, ancestors: tuple[Node, ...], parent_path: tuple[str, ...],
              parent_opacity: float):
        effective_opacity = parent_opacity * node.opacity
        if effective_opacity <= .015:
            return
        path_parts = parent_path + ((node.role,) if node.role != "decor" else ())
        block = node.props.get("block")
        if isinstance(block, TextBlock) and not block.truncated:
            path = "/".join(path_parts) or node.role
            try:
                # Word.x already includes alignment within the full text column.
                # Translate from the renderer's block origin (props x/y), not
                # the narrower painted-bounds metadata, or centered copy is
                # centered twice in the measured ink geometry.
                if "x" in node.props and "y" in node.props:
                    origin_x = float(node.props["x"])
                    origin_y = float(node.props["y"])
                else:
                    origin = node.meta.get("bounds")
                    if origin and len(origin) == 4:
                        origin_x, origin_y = float(origin[0]), float(origin[1])
                    else:
                        raise ValueError("missing text block scene origin")
                transform = Affine2D(e=origin_x, f=origin_y,
                                     source=Space.LOCAL, target=Space.LOCAL)
                for current in (node,) + tuple(reversed(ancestors)):
                    edge = current.local_to_parent_transform()
                    edge_local = Affine2D(edge.a, edge.b, edge.c, edge.d,
                                          edge.e, edge.f,
                                          Space.LOCAL, Space.LOCAL)
                    transform = transform.then(edge_local)
                report = check_text_block(block, FontBook(), (safe_polygon,),
                                           transform=transform)
                failures = tuple((failure.line_index, failure.word_index,
                                  failure.text, failure.reason)
                                 for failure in report.failures)
                if failures:
                    words = ", ".join(repr(item[2]) for item in failures)
                    key = (local_frame, path, failures)
                    if key not in seen:
                        seen.add(key)
                        issues.append(Issue(
                            "text_ink_safe_area", "error",
                            f"Text {path!r} has word ink outside the layout safe rectangle: {words}.",
                            built.index + 1, round(time, 3), [path],
                            "Move or reflow the text so every word's ink fits inside the safe rectangle.",
                            local_frame))
            except Exception as exc:
                # Missing metrics and invalid transforms are actionable QA failures,
                # not grounds for silently omitting this text block.
                key = (local_frame, path, str(exc))
                if key not in seen:
                    seen.add(key)
                    issues.append(Issue(
                        "text_ink_safe_area", "error",
                        f"Text {path!r} ink geometry could not be checked: {exc}.",
                        built.index + 1, round(time, 3), [path],
                        "Restore valid font metrics, text placement and transforms.",
                        local_frame))
        for child in node.children:
            visit(child, ancestors + (node,), path_parts, effective_opacity)

    for root in roots:
        visit(root, (), (), 1.0)
    return issues
