"""Automated visual and editorial QA for the studio renderer.

The report is explicit about what it cannot judge. It checks collisions, safe
areas, typography overflow, measured contrast, cue timing, declared data
consistency, asset provenance and motion variety. Aesthetic judgement remains a
human responsibility.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from ..core.scene_graph import collect_qa_elements, Node
from ..core.timeline import Timeline
from ..design.color import contrast_ratio, relative_luminance
from ..design.tokens import DesignTokens
from ..motionkit.choreography import variety_report
from ..textkit.typesetter import TextBlock

MIN_HOLD = .42
MAX_READING_CPS = 22.0
CONTRAST_LARGE = 3.0
CONTRAST_SMALL = 4.5


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    scene: int | None = None
    time: float | None = None
    elements: list[str] = field(default_factory=list)
    suggestion: str = ""
    frame: int | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code, "severity": self.severity,
            "message": self.message, "scene": self.scene,
            "time": self.time, "elements": list(self.elements),
            "suggestion": self.suggestion, "frame": self.frame,
        }


def _median_colour(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not pixels:
        return (0, 0, 0)
    pixels = sorted(pixels, key=relative_luminance)
    return pixels[len(pixels) // 2]


def _ring_pixels(image: Image.Image, box, thickness: int = 5):
    x0, y0, x1, y1 = (round(value) for value in box)
    width, height = image.size
    # Sample a ring outside the glyph box so anti-aliased text pixels do not
    # masquerade as the backdrop and depress the measured contrast.
    x0, y0 = max(0, x0 - thickness), max(0, y0 - thickness)
    x1, y1 = min(width, x1 + thickness), min(height, y1 + thickness)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return []
    crop = image.crop((x0, y0, x1, y1)).convert("RGB")
    pixels = []
    cw, ch = crop.size
    data = crop.load()
    for y in range(ch):
        for x in range(cw):
            if x < thickness or y < thickness or x >= cw - thickness or y >= ch - thickness:
                pixels.append(data[x, y])
    return pixels


def _safe_box(rect) -> tuple[float, float, float, float]:
    return (rect.x, rect.y, rect.right, rect.bottom)


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
            result.append((node.role, block))
    return result


def audit(project, built_scenes, timeline: Timeline, *,
          renderer=None, samples_per_scene: int = 6,
          strict: bool = False) -> dict:
    """Return a structured, actionable QA report."""
    if not built_scenes:
        raise ValueError("QA requires at least one built scene")
    if len(built_scenes) != len(timeline.scenes):
        raise ValueError("Built scenes and timeline length differ")
    issues: list[Issue] = []
    scenes_report = []
    compositions = []
    sampled_frames = 0
    frames_dir = []
    allowed = _allowed_overlaps(project)

    for built, timing in zip(built_scenes, timeline.scenes):
        scene_issues = []
        elements_seen: dict[str, dict] = {}
        compositions.append(built.layout.recipe)
        # ---------------------------------------------------------- geometry
        samples = sorted({round((timing.frames - 1) * step /
                                max(1, samples_per_scene - 1))
                          for step in range(samples_per_scene)})
        for local_frame in samples:
            time = local_frame / timeline.fps
            nodes = built.at(time)
            elements = []
            for node in nodes:
                elements.extend(collect_qa_elements(node))
            sampled_frames += 1
            scene_issues.extend(_collisions(elements, allowed, built, time,
                                            local_frame))
            scene_issues.extend(_safe_area(elements, built, time, local_frame))
            for element in elements:
                elements_seen.setdefault(element["role"], element)
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
        # -------------------------------------------------------------- timing
        for role, entry in built.choreography.entries.items():
            window = built.duration - entry.settle
            if window < MIN_HOLD:
                scene_issues.append(Issue(
                    "reading_hold_short", "error",
                    (f"{role!r} settles with only {window:.2f}s before the cut "
                     f"(minimum {MIN_HOLD:.2f}s)."),
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
        if renderer is not None:
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
                "composition": built.layout.recipe,
                "type": built.meta.get("type"),
                "issues": [issue.to_dict() for issue in scene_issues],
            })
        issues.extend(scene_issues)

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
            "Music ducking and sidechain pumping are not measured here.",
            "Auto contrast samples a border ring around each text block; extreme "
            "gradients may need a manual check.",
        ],
    }
    return report


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
    tolerance = 1.5
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


def _contrast(elements: list[dict], frame: Image.Image, built,
              time: float, fps: int, *, design_scale: float = 1.0) -> list[Issue]:
    issues = []
    for element in elements:
        # Transient entrance states are intentionally semi-transparent; only
        # judge contrast once the element has settled into its readable state.
        if element["opacity"] < .98:
            continue
        colour = element["meta"].get("color")
        if not colour:
            continue
        size = float(element["meta"].get("size", 24)) / max(1e-6, design_scale)
        weight = element["meta"].get("weight", "regular")
        threshold = CONTRAST_LARGE if (size >= 32 or (size >= 24 and weight == "bold"))\
            else CONTRAST_SMALL
        pixels = _ring_pixels(frame, element["bounds"], thickness=5)
        if not pixels:
            continue
        background = _median_colour(pixels)
        ratio = contrast_ratio(tuple(colour[:3]), background)
        if ratio + 1e-6 < threshold:
            issues.append(Issue(
                "contrast_low", "error",
                (f"{element.get('path', element['role'])!r} has {ratio:.2f}:1 against the sampled "
                 f"backdrop; {threshold:.1f}:1 required at this size."),
                built.index + 1, round(time, 3),
                [element.get("path", element["role"])],
                "Use the accessible accent variant or a contextual scrim/panel.",
                round(time * fps)))
    return issues


def _data_checks(built) -> list[Issue]:
    issues = []
    scene = built.scene
    meta = built.meta
    if meta.get("component") == "breakdown":
        items = meta.get("items") or []
        total = float(meta.get("total", 0))
        if items and abs(sum(float(item["value"]) for item in items) - total) > .01:
            issues.append(Issue(
                "declared_data_mismatch", "error",
                "Breakdown items do not sum to the declared total.",
                built.index + 1, None, [],
                "Correct the manifest values before rendering."))
    if meta.get("component") == "timeline" and scene.get("budget_consumption_shown"):
        issues.append(Issue(
            "unverified_data_visualisation", "error",
            "The scene claims budget consumption without verified data.",
            built.index + 1, None, [],
            "Remove the consumption bar or provide an audited data source."))
    for key in ("value", "total", "percent"):
        if key in meta:
            value = meta[key]
            if isinstance(value, (int, float)) and not math.isfinite(float(value)):
                issues.append(Issue(
                    "invalid_number", "error", f"{key} is not a finite number.",
                    built.index + 1, None, [], "Fix the manifest value."))
    return issues


def _asset_checks(built, project) -> list[Issue]:
    issues = []
    background = built.background
    if background.get("kind") == "photo":
        asset = Path(background.get("asset", ""))
        if not asset.is_file():
            issues.append(Issue(
                "missing_asset", "error",
                f"Background asset is missing: {asset}",
                built.index + 1, None, [],
                "Restore the media file or point the manifest at an approved asset."))
        manager = getattr(project, "asset_manager", None)
        if manager is not None:
            reviewed_path = background.get("video_source") or asset
            review = manager.reviews.get(
                _relative_asset(manager, Path(reviewed_path)), {})
            state = review.get("type", "unreviewed")
            if state == "finished_promo" and not built.scene.get("allow_prebranded"):
                issues.append(Issue(
                    "prebranded_footage", "error",
                    "A finished promo with burned-in graphics is used as a background.",
                    built.index + 1, None, [],
                    "Use clean source footage or explicitly accept the baked-in branding."))
            elif state == "unreviewed" and not built.scene.get("allow_unreviewed"):
                issues.append(Issue(
                    "asset_unreviewed", "warning",
                    "Background footage has no editorial review record.",
                    built.index + 1, None, [],
                    "Inspect actual frames and record editorial_state before publishing."))
    return issues


def _relative_asset(manager, path: Path) -> str:
    try:
        return path.resolve().relative_to(manager.brand_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_summary(project) -> dict:
    manager = getattr(project, "asset_manager", None)
    if manager is None:
        return {"status": "not_available"}
    return {"status": "ok", **manager.summary()}


def _audio_report(project, timeline: Timeline) -> dict:
    audio = getattr(project, "audio", None) or {}
    voiceover = audio.get("voiceover")
    music = audio.get("music")
    sfx = audio.get("sfx") or []
    report = {"voiceover": None, "music": None,
              "sfx": [{"path": item.get("file"),
                       "time": item.get("time", item.get("start", 0)),
                       "measured": False} for item in sfx],
              "status": "not_configured"}
    if voiceover:
        voice_path = voiceover.get("file") or voiceover.get("path") \
            if isinstance(voiceover, dict) else voiceover
        report["voiceover"] = _measure_audio(Path(voice_path), timeline.duration)
    if music:
        music_path = music.get("file") or music.get("path") \
            if isinstance(music, dict) else music
        report["music"] = {"path": str(music_path), "measured": False,
                           "note": "Music level is checked during final human review."}
    if voiceover or music or sfx:
        report["status"] = "technical_checks_only"
    return report


def _measure_audio(path: Path, video_duration: float) -> dict:
    if not path.is_file():
        return {"path": str(path), "status": "missing"}
    try:
        completed = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
             "-af", "volumedetect", "-f", "null", "-"],
            text=True, capture_output=True, check=False)
        if completed.returncode:
            return {"path": str(path), "status": "error",
                    "message": "FFmpeg could not measure the voiceover."}
        output = completed.stderr
        mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", output)
        peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", output)
        duration = None
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            text=True, capture_output=True, check=False)
        if probe.returncode == 0:
            try:
                duration = float(probe.stdout.strip())
            except ValueError:
                duration = None
        result = {
            "path": str(path), "status": "ok",
            "duration": round(duration, 4) if duration else None,
            "mean_db": float(mean.group(1)) if mean else None,
            "peak_db": float(peak.group(1)) if peak else None,
        }
        if duration is not None and duration < video_duration - 1.0:
            result["status"] = "short"
            result["message"] = "Voiceover is shorter than the video timeline."
        if result["peak_db"] is not None and result["peak_db"] > -.1:
            result["status"] = "clipping"
            result["message"] = "Voiceover peaks at or above 0 dBFS."
        if result["mean_db"] is not None and result["mean_db"] < -30:
            result.setdefault("message", "Voiceover is unusually quiet.")
        return result
    except OSError as exc:
        return {"path": str(path), "status": "error", "message": str(exc)}


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
                          if item.get("time") is not None), issues[0])
            time = float(issue.get("time") or 0.0)
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
