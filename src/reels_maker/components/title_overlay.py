"""Build studio-scene-graph title overlays for the classic video renderer.

The source video remains an FFmpeg stream. Only its text/logo overlay is
authored by the shared studio layout, typography and choreography primitives.
This is the compatibility bridge for the opt-in ``render --title-engine studio``
path; the original card renderer remains the default.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PIL import Image

from ..brand import apply_brand
from ..canvas_layout import resolve_safe_areas
from ..core.scene_graph import Node
from ..design.color import ensure_contrast, mix, parse_hex
from ..design.styles import canonical_style
from ..design.tokens import resolve_tokens
from ..layout.engine import LayoutEngine, Rect
from ..motionkit.choreography import ElementSpec, plan_choreography
from ..motionkit.presets import apply_entrance, canonical_preset
from ..spec import Project
from ..textkit.typesetter import FontBook, Run, typeset_runs
from .base import (
    BuiltScene, SceneContext, image_node, measure_text, resolve_text_style,
    rich_text_node, text_node,
)


def _runs(value, *, ink, accent, muted) -> list[Run] | None:
    if not isinstance(value, dict) or not isinstance(value.get("runs"), list):
        return None
    result = []
    for item in value["runs"]:
        if not isinstance(item, dict):
            raise ValueError("title.headline.runs entries must be objects")
        color = {"white": ink, "accent": accent, "muted": muted}.get(
            item.get("color", "white"), ink)
        result.append(Run(
            str(item.get("text", "")), float(item.get("scale", 1.0)), color,
            item.get("weight", "bold"),
            bool(item.get("break_before", False))))
    return result


def build_title_overlay(project: Project, scene: dict, *, index: int,
                        duration: float, logo: Path | None) -> BuiltScene:
    """Translate one classic title card into measured studio scene nodes."""
    from ..cards import resolve_title_style

    title = resolve_title_style(project, scene.get("title") or {})
    if not isinstance(title, dict):
        raise ValueError("Scene title must be an object")
    style_name = canonical_style(project.branding.get(
        "motion_style", "editorial-premium"))
    theme = title.get("theme", "dark")
    if theme not in ("light", "dark"):
        raise ValueError("Title theme must be light or dark")
    is_light = theme == "light"
    base = parse_hex("#F7F7F2" if is_light else "#101A14")
    accent_raw = project.branding.get("accent", "#47A013")
    accent = ensure_contrast(parse_hex(accent_raw), base, 4.5 if is_light else 4.5)
    ink = (20, 34, 26) if is_light else (255, 255, 255)
    muted = mix(ink, base, .36 if is_light else .22)
    safe_margin, safe_top, safe_bottom = resolve_safe_areas(
        project.width, project.height,
        project.branding.get("safe_areas", {}))
    safe = {"horizontal": safe_margin / project.width,
            "top": safe_top / project.height,
            "bottom": safe_bottom / project.height}
    overrides = {"safe": safe}
    if title.get("headline_style", "standard") == "standard":
        from ..design.styles import STYLE_SYSTEMS
        overrides["display"] = STYLE_SYSTEMS[style_name].typography.title
    tokens = resolve_tokens(
        style_name,
        {"palette": {"accent": accent_raw,
                     "background": "#F2F5F0" if is_light else "#101A14"}},
        width=project.width, height=project.height, overrides=overrides)
    typography = project.branding
    fonts = FontBook(
        regular=typography.get("font_regular"),
        bold=typography.get("font_bold"),
        family=typography.get("font_family"))
    body_copy = "\n".join(str(value) for value in
                          (title.get("body"), title.get("footer"))
                          if value)
    headline = title.get("headline", "")
    headline_copy = (" ".join(str(run.get("text", ""))
                               for run in headline.get("runs", []))
                     if isinstance(headline, dict) else str(headline or ""))
    headline_role = ("hero" if title.get("headline_style") == "hero"
                     else "title")
    headline_style = resolve_text_style(
        tokens, headline_role, ink, align="center", balance=True)
    # On moving imagery use the neutral keyline ink for dark scenes; brand
    # green remains a decor accent rather than small copy on unknown pixels.
    kicker_ink = accent if is_light else ink
    kicker_style = resolve_text_style(tokens, "kicker", kicker_ink,
                                      align="center")
    body_style = resolve_text_style(tokens, "body", muted,
                                    align="center", line_height=1.25)
    run_list = _runs(headline, ink=ink, accent=accent, muted=muted)
    text_width = project.width - 2 * safe_margin
    if run_list:
        headline_block = typeset_runs(run_list, headline_style, text_width, fonts)
        headline_measure = (headline_block.width, headline_block.height)
    else:
        headline_measure = measure_text(headline_copy, headline_style,
                                        text_width, fonts)
    measurements = {
        "headline": headline_measure,
        "body": measure_text(body_copy, body_style,
                             project.width - 2 * safe_margin, fonts),
    }
    if title.get("kicker"):
        measurements["kicker"] = measure_text(
            str(title["kicker"]), kicker_style,
            project.width - 2 * safe_margin, fonts)
    position = title.get("position", "lower")
    recipe = {"upper": "full-bleed-type", "middle": "stack-center",
              "lower": "spotlight"}.get(position)
    if recipe is None:
        raise ValueError("Title position must be upper, middle or lower")
    context_scene = {"type": "statement", "duration": duration,
                     "theme": theme, "decor": False,
                     "background": {"kind": "solid", "color": base}}
    context = SceneContext(
        project.width, project.height, project.fps, duration, tokens,
        style_name, fonts, scene_index=index, seed=index * 17 + 3,
        scene=context_scene)
    engine = context.layout
    layout = engine.layout(recipe, measurements)
    elements: dict[str, Node] = {}
    if title.get("kicker") and layout.optional("kicker"):
        kicker = text_node("kicker", str(title["kicker"]), kicker_style,
                           layout.region("kicker"), fonts,
                           align="center", valign="center")
        if kicker:
            elements["kicker"] = kicker
    if headline_copy:
        headline_region = layout.region("headline")
        elements["headline"] = (
            rich_text_node("headline", run_list, headline_style,
                           headline_region, fonts, align="center")
            if run_list else text_node(
                "headline", headline_copy, headline_style, headline_region,
                fonts, align="center", valign="center"))
    if body_copy and layout.optional("body"):
        body = text_node("body", body_copy, body_style,
                         layout.region("body"), fonts,
                         align="center", valign="center")
        if body:
            elements["body"] = body

    warnings = []
    if logo and title.get("logo", True) and not is_light:
        with Image.open(logo) as logo_image:
            aspect = logo_image.width / max(1, logo_image.height)
        logo_w = min(layout.safe.w * .20, tokens.px(200))
        logo_h = logo_w / max(.1, aspect)
        logo_rect = Rect(layout.safe.right - logo_w, layout.safe.y,
                         logo_w, logo_h)
        elements["logo"] = image_node("logo", str(logo), logo_rect)
    elif logo and title.get("logo", True) and is_light:
        warnings.append({
            "code": "light_scene_logo_suppressed",
            "message": "White brand logo suppressed on a light title theme.",
        })
    if title.get("accent_rule", True):
        headline_region = layout.optional("headline")
        if headline_region:
            elements["accent-rule"] = Node(
                kind="round", role="accent-rule",
                props={"x": layout.safe.x,
                       "y": max(layout.safe.y,
                                headline_region.y - tokens.space("xs")),
                       "w": min(layout.safe.w * .22, tokens.px(180)),
                       "h": tokens.stroke["line"],
                       "r": tokens.px(2), "fill": accent},
                qa_class="decor")

    motion = scene.get("motion") or {}
    if not isinstance(motion, dict):
        raise ValueError("Legacy scene motion must be an object")
    preset_aliases = {
        "editorial_reveal": "mask-rise", "fade_stagger": "fade-up",
        "rise_soft": "rise", "slide_left": "slide-left",
        "slide_right": "slide-right", "kinetic_rise": "pop-settle",
    }
    requested_preset = preset_aliases.get(motion.get("preset"))
    if requested_preset:
        requested_preset = canonical_preset(requested_preset)
    motion_tokens = tokens
    if motion.get("duration_frames") or motion.get("stagger_frames"):
        motion_tokens = replace(tokens, motion=replace(
            tokens.motion,
            enter=(motion.get("duration_frames", max(2, round(tokens.motion.enter * project.fps)))
                   / project.fps),
            stagger=(motion.get("stagger_frames", max(0, round(tokens.motion.stagger * project.fps)))
                     / project.fps)))
    specs = []
    def spec(role, weight, kind):
        return ElementSpec(role, weight=weight, kind=kind,
                           hint=requested_preset if role != "logo" else None)
    if "headline" in elements:
        specs.append(spec("headline", 10, "display"))
    if "kicker" in elements:
        specs.append(spec("kicker", 6, "support"))
    if "body" in elements:
        specs.append(spec("body", 4, "support"))
    if "logo" in elements:
        specs.append(spec("logo", 2, "decor"))
    if "accent-rule" in elements:
        specs.append(spec("accent-rule", 1, "decor"))
    raw_cues = motion.get("cue_seconds") or {}
    raw_frames = motion.get("cue_frames") or {}
    if raw_cues and raw_frames:
        raise ValueError("Legacy title motion cannot combine cue_seconds and cue_frames")
    cue_source = raw_cues or raw_frames
    role_map = {"headline": "headline", "kicker": "kicker", "body": "body",
                "footer": "body", "logo": "logo", "accent": "accent-rule"}
    cues = {}
    warning_roles = []
    available = {item.role for item in specs}
    for source_role, value in cue_source.items():
        target_role = role_map.get(source_role)
        if source_role.startswith("headline-"):
            target_role = "headline"
        if target_role not in available:
            warning_roles.append(source_role)
            continue
        seconds = value / project.fps if raw_frames else float(value)
        cues[target_role] = min(cues.get(target_role, seconds), seconds)
    choreography = plan_choreography(
        specs, style=style_name, scene_index=index,
        scene_duration=duration, tokens=motion_tokens, cues=cues)
    distance = motion.get("distance_px")
    for role, node in elements.items():
        entry = choreography.entries.get(role)
        if entry:
            apply_entrance(node, entry.preset, entry.onset, entry.duration,
                           motion_tokens, seed=index * 17 + 3,
                           distance=distance)
            node.meta["motion"] = entry.preset
    if warning_roles:
        warnings.append({
            "code": "legacy_title_cue_without_element",
            "roles": warning_roles,
            "message": "Some legacy title cues have no equivalent studio layer.",
        })
    nodes: list[Node] = []
    backdrop = title.get("backdrop", "none")
    if backdrop in ("soft", "strong"):
        if position == "lower" and "kicker" in elements:
            groups = (("kicker-backdrop", ("kicker",)),
                      ("title-backdrop", ("headline", "body")))
        else:
            groups = (("title-backdrop", ("kicker", "headline", "body")),)
        for role, region_names in groups:
            boxes = [layout.optional(name) for name in region_names
                     if name in elements]
            boxes = [box for box in boxes if box is not None]
            if not boxes:
                continue
            y0 = min(box.y for box in boxes)
            y1 = max(box.bottom for box in boxes)
            inset = tokens.space("sm")
            x0, x1 = layout.safe.x, layout.safe.right
            rect_y = max(layout.safe.y, y0 - inset)
            rect_bottom = min(layout.safe.bottom, y1 + inset)
            nodes.append(Node(
                kind="round", role=role,
                props={"x": x0, "y": rect_y, "w": x1 - x0,
                       "h": max(1, rect_bottom - rect_y),
                       "r": tokens.radius("md"),
                       "fill": (0, 0, 0) if not is_light else (255, 255, 255)},
                 opacity=.48 if backdrop == "soft" else .68,
                 qa_class="decor"))
    nodes.extend(elements.values())
    choreography.warnings.extend(warnings)
    return BuiltScene(
        index=index, scene=scene, context=context, layout=layout,
        background={"kind": "transparent"}, nodes=nodes,
        elements=elements, choreography=choreography,
        meta={"component": "legacy-title-overlay", "position": position})
