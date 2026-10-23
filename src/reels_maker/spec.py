"""Validate manifest settings before a render starts."""
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .motion_timing import build_cue_schedule, scripted_text_roles


class ProjectError(ValueError):
    pass


@dataclass(frozen=True)
class Project:
    name: str
    width: int
    height: int
    fps: int
    scenes: list[dict]
    music: dict | None
    branding: dict
    output: str
    brand: str | None = None
    voiceover: dict | None = None

    @property
    def duration(self) -> float:
        return sum(float(scene["duration"]) for scene in self.scenes)


def load_project(path: str | Path) -> Project:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectError(f"Cannot read project manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectError("Manifest must be a JSON object")
    video = data.get("video", {})
    if not isinstance(video, dict):
        raise ProjectError("video must be an object")
    width, height, fps = (video.get("width", 1080), video.get("height", 1920),
                          video.get("fps", 25))
    for key, val in (("width", width), ("height", height), ("fps", fps)):
        if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
            raise ProjectError(f"{key} must be a positive integer")
    if width > 4096 or height > 4096 or fps > 120 or width % 2 or height % 2:
        raise ProjectError("Video dimensions must be even and <=4096; FPS <=120")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ProjectError("A nonempty scenes list is required")
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or not isinstance(scene.get("file"), str):
            raise ProjectError(f"scene {index}: file is required")
        for field in ("duration", "start"):
            number = scene.get(field, 0 if field == "start" else None)
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise ProjectError(f"scene {index}: {field} must be numeric")
            if (not math.isfinite(number) or
                    (field == "duration" and number <= 0) or number < 0):
                raise ProjectError(f"scene {index}: invalid {field}")
        if scene.get("framing", "crop") not in ("crop", "pad"):
            raise ProjectError(f"scene {index}: framing must be crop or pad")
        transition = scene.get("transition_in")
        if transition is not None:
            if index == 0:
                raise ProjectError("First scene cannot have transition_in")
            if not isinstance(transition, dict):
                raise ProjectError(f"scene {index}: transition_in must be an object")
            kind = transition.get("type")
            allowed = ("cut", "dissolve", "dip_to_black",
                       "motion_wipe_left", "motion_wipe_right")
            if kind not in allowed:
                raise ProjectError(f"scene {index}: unsupported transition {kind!r}")
            if kind == "cut":
                if set(transition) != {"type"}:
                    raise ProjectError(f"scene {index}: cut has no other settings")
            else:
                count = transition.get("frames")
                if (set(transition) != {"type", "frames"} or isinstance(count, bool)
                        or not isinstance(count, int)):
                    raise ProjectError(f"scene {index}: transition requires integer frames")
                if count < 2 or count > max(2, int(fps * .35)):
                    raise ProjectError(f"scene {index}: effect longer than 0.35s")

        title = scene.get("title", {})
        if not isinstance(title, dict):
            raise ProjectError(f"scene {index}: title must be an object")
        if title.get("theme", "dark") not in ("light", "dark"):
            raise ProjectError(f"scene {index}: title.theme must be light or dark")
        if title.get("position", "lower") not in ("upper", "middle", "lower"):
            raise ProjectError(f"scene {index}: title.position must be upper, middle or lower")
        if title.get("headline_style", "standard") not in ("standard", "hero"):
            raise ProjectError(f"scene {index}: title.headline_style must be standard or hero")
        if type(title.get("logo", True)) is not bool:
            raise ProjectError(f"scene {index}: title.logo must be boolean")
        if type(title.get("accent_rule", True)) is not bool:
            raise ProjectError(f"scene {index}: title.accent_rule must be boolean")
        if title.get("backdrop", "none" if title.get("theme") == "light" else "soft") not in ("soft", "strong", "none"):
            raise ProjectError(
                f"scene {index}: title.backdrop must be soft, strong or none")
        if title.get("theme") == "light" and title.get("backdrop", "none") != "none":
            raise ProjectError(f"scene {index}: light title theme requires backdrop=none")
        for field in ("kicker", "headline", "body", "footer"):
            value = title.get(field)
            if value is None:
                continue
            if field == "headline" and isinstance(value, dict):
                if set(value) != {"runs"} or not isinstance(value["runs"], list):
                    raise ProjectError(f"scene {index}: headline requires runs array")
                if scene.get("motion") is not None and len(value["runs"]) > 8:
                    raise ProjectError(
                        f"scene {index}: animated headline supports <=8 runs")
                if not 1 <= len(value["runs"]) <= 16:
                    raise ProjectError(f"scene {index}: headline requires 1..16 runs")
                for run in value["runs"]:
                    if not isinstance(run, dict) or not set(run).issubset(
                            {"text", "scale", "color", "weight", "break_before"}):
                        raise ProjectError(f"scene {index}: invalid headline run")
                    text = run.get("text")
                    if not isinstance(text, str) or not text.strip() or len(text) > 120:
                        raise ProjectError(f"scene {index}: invalid headline run text")
                    scale = run.get("scale", 1.0)
                    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not .65 <= scale <= 1.45:
                        raise ProjectError(f"scene {index}: run scale must be 0.65..1.45")
                    if run.get("color", "white") not in ("white", "accent", "muted"):
                        raise ProjectError(f"scene {index}: invalid run color")
                    if run.get("weight", "bold") not in ("bold", "regular"):
                        raise ProjectError(f"scene {index}: invalid run weight")
                    if type(run.get("break_before", False)) is not bool:
                        raise ProjectError(f"scene {index}: break_before must be boolean")
            elif not isinstance(value, str):
                raise ProjectError(f"scene {index}: {field} must be text")

        motion = scene.get("motion")
        if motion is not None:
            if not isinstance(motion, dict) or motion.get("preset") not in (
                    "editorial_reveal", "fade_stagger", "rise_soft",
                    "slide_left", "slide_right", "kinetic_rise"):
                raise ProjectError(f"scene {index}: unsupported motion preset")
            if not set(motion).issubset(
                    {"preset", "duration_frames", "stagger_frames",
                     "distance_px", "cue_frames", "cue_seconds"}):
                raise ProjectError(f"scene {index}: unknown motion setting")
            for field, default, minimum, maximum in (
                    ("duration_frames", max(2, round(fps * .24)), 2, max(2, round(fps * .45))),
                    ("stagger_frames", max(1, round(fps * .07)), 0, max(1, round(fps * .15))),
                    ("distance_px", 28, 0, 64)):
                value = motion.get(field, default)
                if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                    raise ProjectError(f"scene {index}: invalid motion.{field}")
            if motion["preset"] == "fade_stagger" and motion.get("distance_px", 0):
                raise ProjectError("fade_stagger does not accept nonzero distance_px")
            # Reject ambiguous/mistimed narration cues at manifest parse time,
            # long before allocating any video encoders.
            roles = (["logo", "accent"] +
                     [role for role, _ in scripted_text_roles(title)])
            try:
                build_cue_schedule(
                    motion, roles, fps, round(scene["duration"] * fps))
            except ValueError as exc:
                raise ProjectError(f"scene {index}: {exc}") from exc

    music = data.get("music")
    if music is not None:
        if not isinstance(music, dict) or not isinstance(music.get("file"), str):
            raise ProjectError("music.file is required")
        for field in ("start", "volume", "fade_out"):
            val = music.get(field, 0 if field != "volume" else 1)
            if (isinstance(val, bool) or not isinstance(val, (int, float))
                    or not math.isfinite(val) or val < 0):
                raise ProjectError(f"music.{field} must be finite and nonnegative")
        if music.get("volume", 1) > 4:
            raise ProjectError("music.volume must be <=4")
        if music.get("fade_out", 0) > sum(s["duration"] for s in scenes):
            raise ProjectError("music.fade_out exceeds video duration")

    voiceover = data.get("voiceover")
    if voiceover is not None:
        if (not isinstance(voiceover, dict) or
                not isinstance(voiceover.get("file"), str) or
                not voiceover["file"].strip()):
            raise ProjectError("voiceover.file must be a nonempty file path")
        if set(voiceover) - {"file", "start", "offset_seconds", "volume",
                             "sync_marks"}:
            raise ProjectError("voiceover has unsupported settings")
        for key, default, max_val in (
                ("start", 0, 36000), ("offset_seconds", 0, 36000),
                ("volume", 1, 4)):
            value = voiceover.get(key, default)
            if (isinstance(value, bool) or
                    not isinstance(value, (int, float)) or
                    not math.isfinite(value) or not 0 <= value <= max_val):
                raise ProjectError(f"voiceover.{key} must be a finite nonnegative number")
        if voiceover.get("offset_seconds", 0) >= sum(s["duration"] for s in scenes):
            raise ProjectError("voiceover.offset_seconds must precede the end of the video")
        # Word timestamps are intentionally editor-provided, never inferred
        # from the spoken recording or generated from the corresponding text.
        marks = voiceover.get("sync_marks", [])
        if not isinstance(marks, list) or len(marks) > 128:
            raise ProjectError("voiceover.sync_marks must be a list (max 128)")
        seen_marks = set()
        for mark in marks:
            if (not isinstance(mark, dict) or
                    set(mark) - {"scene", "role", "source_seconds", "tolerance_frames"} or
                    not {"scene", "role", "source_seconds"} <= set(mark)):
                raise ProjectError("Invalid voiceover sync mark")
            scene_no = mark["scene"]
            role = mark["role"]
            seconds = mark["source_seconds"]
            tolerance = mark.get("tolerance_frames", 2)
            if type(scene_no) is not int or not 1 <= scene_no <= len(scenes):
                raise ProjectError("voiceover sync mark scene must be 1-based")
            if (not isinstance(role, str) or
                    role not in dict(scripted_text_roles(
                        scenes[scene_no - 1].get("title") or {}))):
                raise ProjectError(f"voiceover sync mark refers to missing text role {role!r}")
            if not scenes[scene_no - 1].get("motion"):
                raise ProjectError("voiceover sync marks require animated text motion")
            if (isinstance(seconds, bool) or
                    not isinstance(seconds, (int, float)) or
                    not math.isfinite(seconds) or
                    not voiceover.get("start", 0) <= seconds <= 36000):
                raise ProjectError("voiceover sync source_seconds must be an absolute source timestamp after trim")
            if type(tolerance) is not int or not 0 <= tolerance <= 6:
                raise ProjectError("voiceover sync tolerance_frames must be 0..6")
            if (scene_no, role) in seen_marks:
                raise ProjectError(f"Duplicate sync mark for scene {scene_no} role {role}")
            seen_marks.add((scene_no, role))

    # When both tracks are supplied, artists may explicitly opt into
    # moderate narration-driven music ducking; nothing is enabled randomly.
    if music:
        if set(music) - {"file", "start", "volume", "fade_out", "ducking"}:
            raise ProjectError("music contains unsupported settings")
        mode = music.get("ducking", "off")
        if mode not in ("off", "sidechain"):
            raise ProjectError("music.ducking must be off or sidechain")
        if mode == "sidechain" and voiceover is None:
            raise ProjectError("Sidechain ducking requires a voiceover track")

    branding = data.get("branding", {})
    if not isinstance(branding, dict):
        raise ProjectError("branding must be an object")
    output = data.get("output", "output/video.mp4")
    if not isinstance(output, str) or not output.endswith(".mp4"):
        raise ProjectError("output must be an MP4 filename")
    name = data.get("name", source.stem)
    if not isinstance(name, str) or not name:
        raise ProjectError("name must be a nonempty string")
    brand = data.get("brand")
    if brand is not None and not isinstance(brand, str):
        raise ProjectError("brand must be a slug string")
    return Project(name, width, height, fps, scenes, music, branding,
                   output, brand, voiceover)
