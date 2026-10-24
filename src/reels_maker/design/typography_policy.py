"""Cited, machine-readable typography rules for authored social video.

Contract operates on real FreeType TextBlock metrics whenever available. It
does not claim to visually rate a composition or enforce website-only WCAG
text-spacing overrides on non-interactive MP4 footage.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib.resources import files


ROLES = ("display", "hero", "title", "subtitle", "body", "caption", "micro", "kicker")


@lru_cache(maxsize=1)
def _load():
    resource = files("reels_maker.design").joinpath("typography_profiles.json")
    with resource.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if data.get("schema_version") != 1 or data.get("design_basis_short_side_px") != 1080:
        raise ValueError("Unsupported typography profile data")
    ids = [s["id"] for s in data["source_references"]]
    if len(ids) != len(set(ids)) or not all(s["url"].startswith("https://") for s in data["source_references"]):
        raise ValueError("Typography references must be traceable to distinct HTTPS sources")
    for name, profile in data["styles"].items():
        if set(profile["roles"]) != set(ROLES):
            raise ValueError(f"Typography profile {name} has missing roles")
        sizes = [profile["roles"][role]["size_px"] for role in
                 ("display", "hero", "title", "subtitle", "body", "caption", "micro")]
        if sizes != sorted(sizes, reverse=True) or min(sizes) <= 0:
            raise ValueError(f"Typography profile {name} must have a descending semantic scale")
        for role, values in profile["roles"].items():
            if values["size_px"] <= 0 or not .9 <= values["line_height"] <= 1.8:
                raise ValueError(f"Invalid font size or leading for {name}/{role}")
    return data


def load_typography_profiles():
    """Public immutable-by-copy configuration with citations and video rules."""
    return copy.deepcopy(_load())


def suggested_typography(style: str, width: int, height: int) -> dict:
    """Return *suggested*, format-aware font sizes and spacing (not renderer overrides)."""
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError("Positive integer canvas dimensions required")
    config = _load()
    selected = style if style in config["styles"] else "editorial-premium"
    factor = min(width, height) / config["design_basis_short_side_px"]
    roles = {}
    for role, item in config["styles"][selected]["roles"].items():
        roles[role] = {**item, "size_px": max(6, round(item["size_px"] * factor))}
    spatial = config["spatial_system"]
    return {
        "style": selected, "width": width, "height": height,
        "scale_factor": round(factor, 6), "roles": roles,
        "stack_gaps_px": [max(1, round(v * factor)) for v in spatial["stack_gaps_px"]],
        "base_grid_px": max(1, round(spatial["base_grid_px"] * factor)),
        "text_baseline_step_px": max(1, round(spatial["text_baseline_step_px"] * factor)),
        "safe_zone_policy": spatial["safe_zone_policy"],
        "note": "Suggested design values, not fixed official platform minima. Inspect actual rendered text.",
    }


def _canonical_role(role: str) -> str | None:
    text = str(role).lower().replace("-", "_").split("/")[-1]
    if text in ("headline", "heading", "heading_main", "hero_word", "main_title"):
        return "headline"
    if text in ROLES:
        return text
    if text in ("support", "supporting", "description", "subheading"):
        return "subtitle"
    if text in ("source", "data_label", "axis_label", "footnote"):
        return "caption"
    return None


def audit_typography_blocks(blocks, *, width: int, height: int) -> list[dict]:
    """Check actual rendered-size/leading/tracking/hierarchy using TextBlocks.

    Uses the short canvas side to scale thresholds to 9:16, 4:5, 1:1 and 16:9.
    Return all findings as structured issues, without destructive style changes.
    """
    if min(width, height) <= 0:
        raise ValueError("Canvas must be positive")
    config = _load()["quality_guardrails"]
    factor = min(width, height) / 1080.0
    found = []
    hierarchy: dict[str, float] = {}

    def add(code, severity, role, message, suggestion):
        found.append({"code": code, "severity": severity, "role": role,
                      "message": message, "suggestion": suggestion})

    for original_role, block in blocks:
        role = _canonical_role(original_role)
        if role is None or block is None or not getattr(block, "text", "").strip():
            continue
        style = block.style
        size = float(style.size)
        line_height = float(style.line_height)
        tracking = float(style.tracking) / size if size > 0 else 0
        lines = len(block.lines)
        hierarchy[role] = max(size, hierarchy.get(role, 0.0))
        hard_floor = config["critical_min_px_1080_short_side"] * factor
        if size + 0.5 < hard_floor:
            add("typography_critical_size", "error", original_role,
                f"Text rasterizes at {size:g}px; below conservative minimum {hard_floor:.1f}px for this canvas.",
                "Increase type size, reduce copy or split the scene; check mobile playback.")
        elif role in config["min_reading_px_1080_short_side"]:
            suggested_floor = config["recommended_reading_px_1080_short_side"][role] * factor
            if size + .5 < suggested_floor:
                add("typography_small_text", "warning", original_role,
                    f"Font size {size:g}px is below recommended {suggested_floor:.1f}px for role {role}.",
                    "Increase font size or shorten copy; inspect at real phone size.")
        if lines > config["max_lines"].get(role, 99):
            add("typography_too_many_lines", "warning", original_role,
                f"Text wraps to {lines} lines (preferred maximum {config['max_lines'][role]}).",
                "Edit down, reflow or split into more shots.")
        if lines >= 2 and line_height < config["text_multiline_min_line_height"]:
            add("typography_tight_leading", "warning", original_role,
                f"Line-height {line_height:.2f} is too tight for multiline text.",
                "Increase leading and verify ascenders/Polish diacritics.")
        if (len(block.text) >= config["long_copy_threshold_characters"]
                and lines >= 3 and line_height < config["long_copy_min_line_height"]):
            add("typography_long_copy_leading", "warning", original_role,
                "Extended multi-line text has compressed line-height.",
                "Use body-like leading or divide content over multiple scenes.")
        if not config["extreme_tracking_min_em"] <= tracking <= config["extreme_tracking_max_em"]:
            add("typography_extreme_tracking", "warning", original_role,
                f"Tracking {tracking:.3f}em may impair readability.",
                "Use font-native kerning; avoid excessive tracking or negative letter overlap.")

    headline = max(hierarchy.get("headline", 0), hierarchy.get("display", 0),
                   hierarchy.get("hero", 0), hierarchy.get("title", 0))
    subtitle = hierarchy.get("subtitle", 0)
    body = hierarchy.get("body", 0)
    if headline and subtitle and headline < subtitle * config["hierarchy_headline_to_subtitle_min_ratio"]:
        add("typography_weak_hierarchy", "warning", "headline",
            "Headline is too close in size to the supporting subtitle.",
            "Create an obvious primary focal point; adjust size, weight or simplify copy.")
    if subtitle and body and subtitle < body * config["hierarchy_subtitle_to_body_min_ratio"]:
        add("typography_subtitle_body_hierarchy", "warning", "subtitle",
            "Subtitle and body size ordering is not clear.",
            "Use consistent semantic levels for supporting copy.")
    return found


def audit_typography_spacing(placements, *, width: int, height: int) -> list[dict]:
    """Warn on cramped vertical stacks based on actual settled text-node bounds.

    Ignore side-by-side elements, intersecting boxes (existing collision QA),
    and small chart/caption labels that belong to a data component.
    """
    if min(width, height) <= 0:
        raise ValueError("Canvas must be positive")
    important = {"headline", "display", "hero", "title", "subtitle", "body", "kicker"}
    items = []
    for role, bounds in placements:
        canonical = _canonical_role(role)
        if canonical not in important or not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
            continue
        x0, y0, x1, y1 = (float(v) for v in bounds)
        if x1 > x0 and y1 > y0:
            items.append((str(role), (x0, y0, x1, y1)))
    issues = []
    min_gap = 12.0 * (min(width, height) / 1080.0)
    for index, (first_role, a) in enumerate(items):
        for second_role, b in items[index + 1:]:
            horizontal_overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            smaller_width = min(a[2] - a[0], b[2] - b[0])
            if horizontal_overlap < smaller_width * 0.3:
                continue
            gap = max(a[1], b[1]) - min(a[3], b[3])
            if 0 <= gap < min_gap:
                issues.append({
                    "code": "typography_cramped_stack", "severity": "warning",
                    "role": f"{first_role}/{second_role}",
                    "message": f"Related text blocks have only {gap:.1f}px vertical space "
                               f"(minimum review threshold {min_gap:.1f}px).",
                    "suggestion": "Increase the vertical gap using system spacing tokens; "
                                  "keep related items grouped and inspect settled frames.",
                })
    return issues


def audit_typography_tokens(tokens) -> list[dict]:
    """Check configured design scales *before* scene creation."""
    sizes = [tokens.typography.size(role) for role in
             ("display", "hero", "title", "subtitle", "body", "caption", "micro")]
    spaces = [tokens.spacing[name] for name in ("xs", "sm", "md", "lg", "xl", "xxl")]
    issues = []
    if any(a <= b for a, b in zip(sizes, sizes[1:])):
        issues.append({"code": "typography_token_hierarchy", "severity": "warning",
                       "role": "tokens", "message": "Semantic font tiers are not strictly descending.",
                       "suggestion": "Keep display > hero > title > subtitle > body > caption > micro."})
    if any(a >= b for a, b in zip(spaces, spaces[1:])):
        issues.append({"code": "typography_token_spacing", "severity": "warning",
                       "role": "tokens", "message": "Spacing tokens are not strictly ascending.",
                       "suggestion": "Restore monotonic design spacing tokens for repeatable rhythm."})
    return issues


def audit_creative_typography(spec: dict) -> list[dict]:
    """Spec-only editorial preflight; never assumes measured pixel geometry."""
    guard = _load()["quality_guardrails"]
    issues = []
    for index, shot in enumerate(spec.get("shots", [])):
        headline = str(shot.get("headline", "")).strip()
        if (len(headline) > guard["content_max_headline_characters"]
                or len(headline.split()) > guard["content_max_headline_words"]):
            issues.append({"severity": "warning", "code": "typography_long_headline",
                           "path": f"$.shots[{index}].headline",
                           "message": "Headline is too long for a single editorial focal point.",
                           "suggestion": "Shorten the hero claim or use a separate explanatory scene."})
        if (len(headline.split()) > guard["max_uppercase_words"]
                and headline.isupper() and any(char.isalpha() for char in headline)):
            issues.append({"severity": "warning", "code": "typography_caps_overuse",
                           "path": f"$.shots[{index}].headline",
                           "message": "Long all-caps headline reduces scanability.",
                           "suggestion": "Use sentence case, or reserve uppercase for one brief emphasized phrase."})
    return issues
