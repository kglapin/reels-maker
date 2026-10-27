"""Top-level QA report orchestration and compatibility exports."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from ..core.scene_graph import Node, collect_qa_elements
from ..core.timeline import Timeline
from ..design.tokens import is_vertical_reels_canvas
from ..design.typography_policy import (
    audit_typography_blocks, audit_typography_spacing, audit_typography_tokens,
)
from ..motionkit.choreography import variety_report
from .assets import _asset_checks, _asset_summary
from .audio import _audio_report
from .contrast import CONTRAST_LARGE, CONTRAST_SMALL, _contrast
from .data import _data_checks
from .geometry import (
    SAFE_AREA_TOLERANCE, _allowed_overlaps, _collisions, _safe_area, _text_blocks,
    _text_ink_safe_area, _vertical_reels_content_zone, sample_geometry_frames,
)
from .models import Issue

MIN_HOLD = .42
MAX_READING_CPS = 22.0

def audit(project, built_scenes, timeline: Timeline, *,
          renderer=None, samples_per_scene: int = 6,
          strict: bool = False) -> dict:
    """Return a structured, actionable QA report."""
    if not built_scenes:
        raise ValueError("QA requires at least one built scene")
    if len(built_scenes) != len(timeline.scenes):
        raise ValueError("Built scenes and timeline length differ")
    if type(samples_per_scene) is not int or samples_per_scene < 2:
        raise ValueError("samples_per_scene must be an integer >= 2")
    issues: list[Issue] = []
    scenes_report = []
    compositions = []
    sampled_frames = 0
    frames_dir = []
    allowed = _allowed_overlaps(project)

    # Camera Canvas is a separate renderer path; its travel, subject-retention
    # and camera-safe geometry checks must be part of the same QA gate rather
    # than living only behind a directly imported helper.
    camera_canvas_mode = any("camera_canvas" in scene for scene in project.scenes)
    if camera_canvas_mode:
        from .camera_canvas import audit_camera_canvas
        camera_report = audit_camera_canvas(
            project.scenes, project.width, project.height, fps=timeline.fps)
        issues.extend(Issue(**item) for item in camera_report["issues"])

    for built, timing in zip(built_scenes, timeline.scenes):
        scene_issues = []
        camera_cfg = built.scene.get("camera_canvas")
        canvas_component = built.meta.get("component")
        if isinstance(camera_cfg, dict):
            composition_name = (
                f"camera-canvas:{camera_cfg.get('layout', 'photo-above')}")
        elif canvas_component in ("note_canvas", "search_canvas"):
            composition_name = canvas_component
        else:
            composition_name = built.layout.recipe
        vertical_reels = is_vertical_reels_canvas(
            built.context.width, built.context.height)
        scene_issues.extend(_vertical_reels_content_zone(built))
        elements_seen: dict[str, dict] = {}
        compositions.append(composition_name)
        # ---------------------------------------------------------- geometry
        samples = sample_geometry_frames(built, timing, timeline.fps,
                                         samples_per_scene)
        for local_frame in samples:
            time = local_frame / timeline.fps
            nodes = built.at(time)
            elements = []
            for node in nodes:
                elements.extend(collect_qa_elements(node))
            sampled_frames += 1
            scene_issues.extend(_collisions(elements, allowed, built, time,
                                            local_frame))
            if not vertical_reels:
                scene_issues.extend(_safe_area(elements, built, time, local_frame))
                scene_issues.extend(_text_ink_safe_area(
                    nodes, built, time, local_frame))
            for element in elements:
                elements_seen.setdefault(element["role"], element)
        for element in elements_seen.values():
            if element["meta"].get("negative_effect"):
                scene_issues.append(Issue(
                    "negative_text_review", "warning",
                    ("Negative/inverted glyph fill depends on the underlying "
                     "image; verify this heavy word at phone size."),
                    built.index + 1, None,
                    [element.get("path", element["role"])],
                    "Keep the effect to one short, bold word and inspect real footage."))
        # --------------------------------------------------------- typography
        root = Node(kind="group", children=built.at(0.0))
        for role, block in _text_blocks(root):
            if block.overflow:
                scene_issues.append(Issue(
                    "text_overflow", "error",
                    f"Text {role!r} overflows its measured column.",
                    built.index + 1, 0.0, [role],
                    "Shorten the copy or reduce the type size for this region."))
            if block.truncated:
                scene_issues.append(Issue(
                    "text_truncated", "error",
                    f"Text {role!r} was truncated by max_lines.",
                    built.index + 1, 0.0, [role],
                    "Remove max_lines or shorten the sentence."))
            if not block.lines:
                scene_issues.append(Issue(
                    "text_empty", "warning", f"Text {role!r} is empty.",
                    built.index + 1, 0.0, [role],
                    "Remove the empty layer from the composition."))
        # Enforce typography policy on the real typeset/ink geometry, not guessed copy lengths.
        for finding in audit_typography_blocks(
                _text_blocks(root), width=project.width, height=project.height):
            scene_issues.append(Issue(
                finding["code"], finding["severity"], finding["message"],
                built.index + 1, None, [finding["role"]], finding["suggestion"]))
        for finding in audit_typography_spacing(
                ((node.role, node.meta.get("bounds")) for node in built.elements.values()),
                width=project.width, height=project.height):
            scene_issues.append(Issue(
                finding["code"], finding["severity"], finding["message"],
                built.index + 1, None, [finding["role"]], finding["suggestion"]))
        # -------------------------------------------------------------- timing
        for role, entry in built.choreography.entries.items():
            exit_entry = built.choreography.exits.get(role)
            # A planned exit keeps the reading window intact: hold counts up
            # to the fade onset, not to the cut.
            readable_until = (exit_entry.onset if exit_entry
                              else built.duration)
            window = readable_until - entry.settle
            if window < MIN_HOLD:
                scene_issues.append(Issue(
                    "reading_hold_short", "error",
                    (f"{role!r} settles with only {window:.2f}s readable "
                     f"hold (minimum {MIN_HOLD:.2f}s)."),
                    built.index + 1, round(entry.settle, 3), [role],
                    "Move the cue earlier, shorten the entrance or extend the shot.",
                    round(entry.settle * timeline.fps)))
            if entry.explicit and entry.onset > built.duration:
                scene_issues.append(Issue(
                    "cue_outside_scene", "error",
                    f"Explicit cue for {role!r} starts after the scene ends.",
                    built.index + 1, round(entry.onset, 3), [role],
                    "Fix the narration transcript or scene duration."))
        # ------------------------------------------------------------- contrast
        if renderer is not None and not camera_canvas_mode:
            probe_times = [round((timing.frames - 1) * part /
                                 max(1, samples_per_scene - 1)) / timeline.fps
                           for part in (1, samples_per_scene - 2,
                                        samples_per_scene - 1)]
            for time in sorted(set(probe_times)):
                frame = renderer.render(built, min(time, built.duration))
                elements = []
                for node in built.at(min(time, built.duration)):
                    elements.extend(collect_qa_elements(node))
                scene_issues.extend(_contrast(
                    elements, frame, built, time, timeline.fps,
                    design_scale=float(getattr(getattr(project, "tokens", None),
                                               "scale", 1.0))))
        # ---------------------------------------------------------------- data
        scene_issues.extend(_data_checks(built))
        # -------------------------------------------------------------- assets
        scene_issues.extend(_asset_checks(built, project))
        if scene_issues:
            scenes_report.append({
                "scene": built.index + 1,
                "composition": composition_name,
                "type": built.meta.get("type"),
                "issues": [issue.to_dict() for issue in scene_issues],
            })
        issues.extend(scene_issues)

    for finding in audit_typography_tokens(project.tokens):
        issues.append(Issue(
            finding["code"], finding["severity"], finding["message"],
            None, None, [finding["role"]], finding["suggestion"]))
    variety = variety_report(built.choreography for built in built_scenes)
    composition_counts: dict[str, int] = {}
    for recipe in compositions:
        composition_counts[recipe] = composition_counts.get(recipe, 0) + 1
    dominant_recipe = max(composition_counts.values(), default=0)
    if compositions and dominant_recipe / len(compositions) > .62:
        issues.append(Issue(
            "composition_monotony", "warning",
            "More than 62% of scenes use the same composition.",
            None, None, [], "Introduce a second composition from the style menu."))
    if variety["status"] == "review":
        issues.append(Issue(
            "motion_monotony", "warning",
            "Motion presets repeat too often across the film.",
            None, None, [], "Vary entrance presets by narrative role."))

    for warning in getattr(project, "warnings", []) or []:
        if isinstance(warning, dict):
            code = str(warning.get("code", "project_warning"))
            message = str(warning.get("message", code))
        else:
            code, message = "project_warning", str(warning)
        issues.append(Issue(code, "warning", message))
    cue_plan = getattr(project, "cue_plan", None)
    if cue_plan is not None:
        for warning in cue_plan.warnings:
            issues.append(Issue(
                str(warning.get("code", "cue_warning")), "warning",
                str(warning.get("message", "Narration cue requires review.")),
                warning.get("scene")))
    audio = _audio_report(project, timeline)
    voice_audio = audio.get("voiceover") or {}
    if voice_audio.get("status") in ("clipping", "missing", "error"):
        issues.append(Issue(
            "voiceover_" + str(voice_audio["status"]), "error",
            voice_audio.get("message", "Voiceover failed technical validation."),
            None, None, [], "Fix the voiceover source or its peak level."))
    elif voice_audio.get("status") == "short":
        issues.append(Issue(
            "voiceover_short", "warning",
            voice_audio.get("message", "Voiceover is shorter than the timeline."),
            None, None, [], "Check the final speech tail and scene timing."))
    elif voice_audio.get("mean_db") is not None and voice_audio["mean_db"] < -30:
        issues.append(Issue(
            "voiceover_quiet", "warning", "Voiceover is unusually quiet.",
            None, None, [], "Listen on a phone and adjust level if needed."))
    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    report = {
        "schema_version": 1,
        "ok": errors == 0,
        "strict": bool(strict),
        "video": {"width": getattr(project, "width", None),
                  "height": getattr(project, "height", None),
                  "fps": timeline.fps,
                  "duration": timeline.duration,
                  "frames": timeline.total_frames},
        "summary": {
            "scenes": len(built_scenes),
            "frames_sampled": sampled_frames,
            "errors": errors,
            "warnings": warnings,
            "status": "pass" if errors == 0 else "review",
        },
        "scenes": scenes_report,
        "issues": [issue.to_dict() for issue in issues],
        "variety": {**variety, "compositions": composition_counts},
        "assets": _asset_summary(project),
        "cues": cue_plan.to_dict() if cue_plan else None,
        "audio": audio,
        "limitations": [
            "Collision, safe-area, contrast and timing checks are deterministic.",
            "Aesthetic quality and brand fit require human review on a phone.",
            *(["Camera Canvas uses its own raster layout; frame-level contrast must be reviewed in its storyboard/MP4, not inferred from the regular scene graph." ]
              if camera_canvas_mode else []),
            "Music ducking and sidechain pumping are not measured here.",
            "Negative glyph fills are image-dependent and require manual contrast review.",
            "Auto contrast samples a border ring around each text block; extreme "
            "gradients may need a manual check.",
        ],
    }
    return report

def contact_sheet(report: dict, built_scenes, renderer, timeline: Timeline,
                  output: Path, *, columns: int = 3,
                  thumb_width: int = 260) -> Path:
    """Render flagged moments plus one representative frame per scene."""
    entries = []
    for scene_report in report.get("scenes", []):
        index = scene_report["scene"] - 1
        issues = scene_report.get("issues") or []
        if issues:
            issue = next((item for item in issues
                          if item.get("severity") == "error"
                          and item.get("time") is not None), None)
            if issue is not None:
                time = float(issue["time"])
            else:
                issue = issues[0]
                time = built_scenes[index].duration * .75
            entries.append((index, time, issue.get("code", "issue")))
        else:
            entries.append((index, built_scenes[index].duration * .75,
                            "representative"))
    if not entries:
        entries = [(index, scene.duration * .75, "representative")
                   for index, scene in enumerate(built_scenes)]
    entries = entries[:18]
    thumbs = []
    for index, time, label in entries:
        built = built_scenes[index]
        frame = renderer.render(built, min(time, built.duration))
        ratio = thumb_width / frame.width
        thumb = frame.resize((thumb_width, max(1, round(frame.height * ratio))),
                             Image.Resampling.LANCZOS).convert("RGB")
        thumbs.append((thumb, f"S{index + 1}  {time:.2f}s  {label}"))
    if not thumbs:
        raise ValueError("No frames available for a contact sheet")
    thumb_height = max(thumb.height for thumb, _ in thumbs)
    rows = math.ceil(len(thumbs) / columns)
    label_h = 34
    sheet = Image.new("RGB", (columns * thumb_width + (columns + 1) * 10,
                              rows * (thumb_height + label_h) + (rows + 1) * 10),
                      (12, 16, 14))
    draw = ImageDraw.Draw(sheet)
    for position, (thumb, label) in enumerate(thumbs):
        row, column = divmod(position, columns)
        x = 10 + column * (thumb_width + 10)
        y = 10 + row * (thumb_height + label_h + 10)
        sheet.paste(thumb, (x, y + label_h))
        draw.text((x, y + 6), label, fill=(220, 240, 225))
    sheet.save(output)
    return output

def write_report(report: dict, output_dir: Path) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "qa-report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return {"report": str(path), "ok": report.get("ok", False)}


# Compatibility exports: existing clients historically imported QA checks
# directly from reels_maker.qa.report.
from .camera_canvas import audit_camera_canvas
from .geometry import (
    _inside_polygon, _overlap_area, _overlaps, _safe_box,
)
from .contrast import _median_colour, _ring_pixels
from .data import audit_data_scene
from .assets import _relative_asset
from .audio import _measure_audio
from .repair import (
    _evaluate_built_scene_qa, repair_scene_layout,
    run_polish_typography_regression,
)
