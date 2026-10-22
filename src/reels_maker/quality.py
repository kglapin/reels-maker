"""Design-quality linting for agent-authored video scripts.

This is a deterministic preflight aid, NOT an aesthetic quality score. It
catches predictable editorial errors before expensive video encoding.
"""
from __future__ import annotations
from .spec import Project
from pathlib import Path
from .asset_reviews import load_media_reviews
from .ffmpeg import RenderError
from .motion_timing import (build_cue_schedule, scripted_text_roles,
                            MIN_SETTLED_SECONDS)

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
        scene_frames = round(scene["duration"] * project.fps)
        motion = scene.get("motion") or {}
        roles = scripted_text_roles(title)
        outgoing = 0
        if index + 1 < len(project.scenes):
            next_fx = project.scenes[index + 1].get("transition_in") or {}
            outgoing = next_fx.get("frames", 0)
        usable_frames = scene_frames - outgoing

        if motion:
            try:
                schedule = build_cue_schedule(
                    motion, ["logo", "accent"] + [role for role, _ in roles],
                    project.fps, scene_frames)
            except ValueError as exc:
                warn("invalid_motion_timing", str(exc), index)
                # Never conceal further legibility failures just because an
                # automatically authored schedule also violates timing rules.
                # A broken timeline should generate actionable warnings for
                # both choreography and the on-screen copy itself.
                warn("no_reading_hold",
                     "Motion schedule cannot guarantee a settled reading window.",
                     index)
                approximate_window = max(
                    0, (usable_frames -
                        motion.get("duration_frames",
                                   max(2, round(project.fps * .24)))) /
                    project.fps)
                if len(message) / MAX_CHARS_PER_SECOND > approximate_window:
                    warn("reading_speed",
                         "On-screen copy is too dense for the available shot.",
                         index)
                continue
            duration_frames = schedule.duration_frames
            text_end = max(
                (schedule.starts[role] + duration_frames for role, _ in roles),
                default=0)
            hold = (usable_frames - text_end) / project.fps
            if hold < MIN_SETTLED_SECONDS:
                warn("no_reading_hold",
                     "Final text settles less than 0.55s before the cut or "
                     "outgoing transition. Re-time the last cue.", index)
            for role, content in roles:
                # A staggered headline should be judged by each phrase's
                # actual available reading time, not as one late static card.
                reading_window = (usable_frames
                    - schedule.starts[role] - duration_frames) / project.fps
                if len(content.strip()) / MAX_CHARS_PER_SECOND > reading_window:
                    warn("reading_speed",
                         f"{role} has insufficient screen time after its cue. "
                         "Shorten copy or reveal it earlier.", index)
        else:
            hold = usable_frames / project.fps
            if hold < MIN_SETTLED_SECONDS:
                warn("no_reading_hold",
                     "Text is visible less than 0.55s before the outgoing "
                     "cut or transition.", index)
            if len(message) / MAX_CHARS_PER_SECOND > hold:
                warn("reading_speed",
                     "Text exceeds a conservative reading-time budget. "
                     "Shorten copy or extend the shot.", index)
        if len(message) > 125:
            warn("text_density", "Scene carries too much on-screen copy.", index)

    # Optional manual word markers can catch real A/V drift that a plain
    # scene-local cue may miss after trimming narration or adding crossfades.
    if (project.voiceover or {}).get("sync_marks"):
        # Local import avoids a module cycle: cue_sheet uses renderer frame
        # quantization and renderer itself imports this quality module.
        from .cue_sheet import make_cue_sheet
        try:
            sync_sheet = make_cue_sheet(project)
        except (ValueError, RenderError) as exc:
            warn("invalid_narration_sync", str(exc))
        else:
            for issue in sync_sheet["warnings"]:
                if issue["code"] in (
                        "narration_cue_drift",
                        "narration_marker_out_of_timeline",
                        "cue_begins_inside_crossfade",
                        "cue_ends_inside_outgoing_transition"):
                    warn(issue["code"], issue["message"], issue.get("scene"))

    return {
        "standard": "editorial-v4",
        "status": "review" if warnings else "pass",
        "warning_count": len(warnings),
        "warnings": warnings,
        "human_review_required": True,
    }
