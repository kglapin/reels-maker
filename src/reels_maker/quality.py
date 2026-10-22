"""Design-quality linting for agent-authored video scripts.

This is a deterministic preflight aid, NOT an aesthetic quality score. It
catches predictable editorial errors before expensive video encoding.
"""
from __future__ import annotations
from .spec import Project
from pathlib import Path
from .asset_reviews import load_media_reviews

MAX_CHARS_PER_SECOND = 19.0
HOLD_SECONDS = 0.55


def _body(title: dict) -> str:
    chunks = []
    for field in ("kicker", "headline", "body", "footer"):
        value = title.get(field, "")
        if isinstance(value, dict):
            chunks.append("".join(str(run["text"]) for run in value.get("runs", [])))
        else:
            chunks.append(str(value or ""))
    return " ".join(chunk.strip() for chunk in chunks if chunk.strip())


def review_project(project: Project, *, root: Path | None = None) -> dict:
    """Return actionable, structured creative warnings, without touching media."""
    warnings = []
    def warn(code, message, scene=None):
        issue = {"code": code, "message": message}
        if scene is not None:
            issue["scene"] = scene
        warnings.append(issue)

    # Transitions use cognitive attention; most edits should remain hard cuts.
    fx = [scene.get("transition_in", {}).get("type", "cut")
          for scene in project.scenes[1:]]
    effects = [kind for kind in fx if kind != "cut"]
    if len(fx) >= 3 and len(effects) > max(1, len(fx) // 3):
        warn("transition_density",
             "More than one third of cuts use effects. Prefer motivated edits.")
    if len(fx) >= 3 and any(fx[i] == fx[i+1] == fx[i+2] != "cut"
                            for i in range(len(fx)-2)):
        warn("repeated_transition",
             "Three consecutive identical transitions risk looking templated.")

    reviewed = (load_media_reviews(project.brand, Path(root).resolve())
                if root is not None and project.brand else {})
    for index, scene in enumerate(project.scenes):
        title = scene.get("title") or {}
        asset = reviewed.get(scene.get("file"), {})
        if asset.get("type") == "finished_promo":
            # Brand projects inherit their logo unless explicitly disabled.
            # Reusing an existing promo WITHOUT adding titles or logos is safe
            # from double-branding (publication rights still need review).
            logo_enabled = bool(project.branding.get("logo", True))
            additions = bool(title) or logo_enabled
            if additions:
                warn(
                    "source_is_prebranded",
                    "Source is a finished promo with pre-existing graphics ("
                    + ", ".join(asset.get("burned_in", []))
                    + "). Use clean master footage; do not add another logo or "
                    "lower-third to this asset.", index)

        message = _body(title)
        if not message:
            continue
        headline = title.get("headline", "")
        rich = headline.get("runs", []) if isinstance(headline, dict) else []
        if rich:
            accented = [run for run in rich if run.get("color") == "accent"]
            oversized = [run for run in rich if run.get("scale", 1) >= 1.2]
            if len(accented) > 2 or len(oversized) > 2:
                warn("too_many_hero_words",
                     "Use one or two highlighted words; reduce emphasis.", index)
            if len(rich) > 6:
                warn("fragmented_typography",
                     "Headline has many style changes; consolidate runs.", index)
        duration = float(scene["duration"])
        motion = scene.get("motion") or {}
        entrance = 0.0
        if motion:
            active = 0
            for field in ("kicker", "headline", "body", "footer"):
                value = title.get(field)
                if isinstance(value, dict):
                    active += len(value.get("runs", []))
                elif value:
                    active += 1
            frames = motion.get("duration_frames", max(2, round(project.fps * .24)))
            stagger = motion.get("stagger_frames", max(1, round(project.fps * .07)))
            entrance = (frames + stagger * max(0, active - 1)) / project.fps
        hold = duration - entrance
        if hold < HOLD_SECONDS:
            warn("no_reading_hold",
                 "Reveal leaves less than 0.55s of settled text. Shorten animation.",
                 index)
        if len(message) / MAX_CHARS_PER_SECOND > hold:
            warn("reading_speed",
                 "Text exceeds a conservative reading-time budget. "
                 "Shorten copy or extend the shot.", index)
        if len(message) > 125:
            warn("text_density", "Scene carries too much on-screen copy.", index)

    return {
        "standard": "editorial-v2",
        "status": "review" if warnings else "pass",
        "warning_count": len(warnings),
        "warnings": warnings,
        "human_review_required": True,
    }
