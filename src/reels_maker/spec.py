"""Validate manifest settings before a render starts."""
import json
from dataclasses import dataclass
from pathlib import Path


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
            if (field == "duration" and number <= 0) or number < 0:
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
    music = data.get("music")
    if music is not None:
        if not isinstance(music, dict) or not isinstance(music.get("file"), str):
            raise ProjectError("music.file is required")
        for field in ("start", "volume", "fade_out"):
            val = music.get(field, 0 if field != "volume" else 1)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or val < 0:
                raise ProjectError(f"music.{field} must be nonnegative")
        if music.get("volume", 1) > 4:
            raise ProjectError("music.volume must be <=4")
        if music.get("fade_out", 0) > sum(s["duration"] for s in scenes):
            raise ProjectError("music.fade_out exceeds video duration")
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
    return Project(name, width, height, fps, scenes, music, branding, output, brand)
