"""High-level studio project loader.

A studio manifest is a superset of the legacy kinetic manifest. It resolves a
brand, a visual style, narration cues and export profile once, then exposes
immutable tokens and built scenes to the renderer and QA.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .assets.manager import AssetManager
from .audiokit.cues import CuePlan, apply_cue_plan, load_transcript, plan_cues
from .components.base import BuiltScene, SceneContext
from .components.scenes import build_scene
from .core.timeline import Timeline, build_timeline
from .design.styles import STYLE_SYSTEMS, canonical_style
from .design.tokens import DesignTokens, resolve_tokens
from .textkit.typesetter import FontBook


PROFILES = {
    "preview": {"width": 360, "height": 640, "fps": 20,
                "purpose": "Fast layout review"},
    "review": {"width": 720, "height": 1280, "fps": 30,
               "purpose": "Animation and readability review"},
    "final": {"width": 1080, "height": 1920, "fps": 30,
              "purpose": "Publication master for Reels"},
    "high-motion": {"width": 1080, "height": 1920, "fps": 60,
                    "purpose": "Selected high-motion sequences"},
}


class StudioError(ValueError):
    pass


@dataclass
class StudioProject:
    path: Path
    root: Path
    name: str
    width: int
    height: int
    fps: int
    style: str
    scenes: list[dict]
    brand: str | None
    brand_data: dict
    audio: dict
    export: dict
    tokens: DesignTokens
    fonts: FontBook
    asset_manager: AssetManager | None
    cue_plan: CuePlan | None = None
    warnings: list[dict] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return sum(float(scene["duration"]) for scene in self.scenes)

    def timeline(self) -> Timeline:
        return build_timeline(self.scenes, self.fps)

    def build(self, timeline: Timeline | None = None) -> list[BuiltScene]:
        timeline = timeline or self.timeline()
        built = []
        for index, (scene, timing) in enumerate(zip(self.scenes, timeline.scenes)):
            context = SceneContext(
                width=self.width, height=self.height, fps=self.fps,
                duration=timing.duration, tokens=self.tokens, style=self.style,
                fonts=self.fonts, scene_index=index, seed=index * 17 + 3,
                assets=self.asset_manager, scene=scene)
            item = build_scene(context, scene)
            transition = scene.get("transition_in")
            if isinstance(transition, dict):
                transition = transition.get("type", "cut")
            if not transition:
                cycle = STYLE_SYSTEMS[self.style].transitions
                transition = cycle[(index + 1) % len(cycle)] if index else "dip"
                previous = built[-1].meta.get("transition_in") if built else None
                if transition == previous:
                    transition = cycle[(index + 2) % len(cycle)]
            item.meta["transition_in"] = transition
            item.meta["transition_duration"] = float(
                scene.get("transition_seconds", .30))
            built.append(item)
        return built

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "brand": self.brand,
            "style": self.style,
            "video": {"width": self.width, "height": self.height,
                      "fps": self.fps, "duration": round(self.duration, 4)},
            "scene_count": len(self.scenes),
            "tokens": self.tokens.to_dict(),
            "audio": {"configured": bool(self.audio)},
            "cues": self.cue_plan.to_dict() if self.cue_plan else None,
            "warnings": list(self.warnings),
        }


def _brand_slug(path: Path, data: dict, root: Path) -> str | None:
    explicit = data.get("brand")
    if explicit:
        slug = str(explicit)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise StudioError(f"Invalid brand slug: {slug!r}")
        return slug
    try:
        relative = path.resolve().relative_to((root / "brands").resolve())
    except ValueError:
        return None
    parts = relative.parts
    return parts[0] if parts else None


def _brand_palette(brand_data: Mapping) -> dict:
    identity = brand_data.get("identity") or {}
    palette = identity.get("palette") or {}
    branding = brand_data.get("branding") or {}
    result = {}
    mapping = {"accent": "primary", "background": "background",
               "ink": "text", "muted": "neutral"}
    for target, source in mapping.items():
        value = palette.get(source)
        if value:
            result[target] = value
    if branding.get("accent"):
        result["accent"] = branding["accent"]
    result.setdefault("surface", "#FFFFFF")
    return result


def _font_book(root: Path, brand_data: Mapping) -> FontBook:
    identity = brand_data.get("identity") or {}
    typography = identity.get("typography") or {}
    primary = str(typography.get("primary", "")).strip()
    family = primary.lower().replace(" ", "") or None
    branding = brand_data.get("branding") or {}
    regular = branding.get("font_regular") or typography.get("regular")
    bold = branding.get("font_bold") or typography.get("bold")
    extra = []
    fonts_dir = root / "brands" / str(brand_data.get("id", "")) / "fonts"
    if fonts_dir.is_dir():
        extra.append(str(fonts_dir))
    return FontBook(regular=regular, bold=bold, family=family,
                    extra_dirs=tuple(extra))


def _resolve_asset(path_value: str, brand_root: Path, root: Path) -> Path:
    value = str(path_value)
    relative = Path(value)
    if relative.is_absolute():
        candidate = relative
    elif value.startswith("brands/"):
        candidate = root / relative
    else:
        candidate = brand_root / relative
    resolved = candidate.resolve()
    allowed_root = brand_root.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise StudioError(
            f"Asset path escapes brand scope: {value!r}") from exc
    if not resolved.is_file():
        raise StudioError(f"Asset does not exist: {value} (looked in {resolved})")
    return resolved


def load_studio(path: str | Path, *, root: str | Path | None = None,
                profile: str | None = None) -> StudioProject:
    path = Path(path).resolve()
    if not path.is_file():
        raise StudioError(f"Manifest does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StudioError(f"Cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise StudioError("Manifest must be a JSON object")
    return _load_studio_data(path, data, root=root, profile=profile)


def _load_studio_data(path: Path, data: dict, *,
                      root: str | Path | None = None,
                      profile: str | None = None) -> StudioProject:
    """Resolve an already parsed manifest (also used by legacy adapters)."""
    path = Path(path).resolve()
    if root is None:
        if "brands" in path.parts:
            position = path.parts.index("brands")
            root = Path(*path.parts[:position]) if position else Path("/")
        else:
            root = Path.cwd()
    root = Path(root).resolve()
    brand = _brand_slug(path, data, root)
    brand_root = root / "brands" / brand if brand else path.parent
    brand_data = {}
    if brand:
        brand_file = brand_root / "brand.json"
        if brand_file.is_file():
            brand_data = json.loads(brand_file.read_text(encoding="utf-8"))
    style = canonical_style(data.get("style") or "kinetic-advertising")
    video = data.get("video") or {}
    if not isinstance(video, dict):
        raise StudioError("video must be an object")
    width = int(video.get("width", 1080))
    height = int(video.get("height", 1920))
    fps = int(video.get("fps", 30))
    export = dict(data.get("export") or {})
    chosen_profile = profile or export.get("profile")
    if chosen_profile:
        if chosen_profile not in PROFILES:
            raise StudioError(f"Unknown export profile {chosen_profile!r}; choose "
                              + ", ".join(sorted(PROFILES)))
        spec = PROFILES[chosen_profile]
        width, height, fps = spec["width"], spec["height"], spec["fps"]
    if not 180 <= width <= 4096 or not 180 <= height <= 4096:
        raise StudioError("Video dimensions must be between 180 and 4096 px")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise StudioError("FPS must be an integer between 1 and 120")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise StudioError("A nonempty scenes list is required")
    scenes = [dict(scene) for scene in scenes]
    for index, scene in enumerate(scenes):
        if "duration" not in scene:
            raise StudioError(f"Scene {index + 1}: duration is required")
        scene.setdefault("index", index + 1)
        if scene.get("logo"):
            scene["logo"] = str(_resolve_asset(str(scene["logo"]),
                                               brand_root, root))
    brand_palette = _brand_palette(brand_data)
    design_overrides = dict(data.get("design_overrides") or {})
    palette_overrides = design_overrides.pop("palette", {})
    if not isinstance(palette_overrides, dict):
        raise StudioError("design_overrides.palette must be an object")
    brand_palette.update(palette_overrides)
    tokens = resolve_tokens(
        style, {"palette": brand_palette} if brand_palette else {},
        width=width, height=height,
        overrides=design_overrides)
    fonts = _font_book(root, brand_data)
    audio = data.get("audio") or {}
    if not isinstance(audio, dict):
        raise StudioError("audio must be an object")
    warnings: list[dict] = list(data.get("_initial_warnings") or [])
    # Resolve audio paths.
    for key in ("voiceover", "music"):
        value = audio.get(key)
        if isinstance(value, dict):
            file_value = value.get("file") or value.get("path")
            if file_value:
                value = dict(value)
                value["file"] = str(_resolve_asset(str(file_value), brand_root, root))
                audio[key] = value
        elif isinstance(value, str):
            audio[key] = str(_resolve_asset(value, brand_root, root))
    sfx = audio.get("sfx") or []
    if not isinstance(sfx, list):
        raise StudioError("audio.sfx must be an array of effect objects")
    resolved_sfx = []
    for index, effect in enumerate(sfx):
        if not isinstance(effect, dict):
            raise StudioError(f"audio.sfx[{index}] must be an object")
        effect = dict(effect)
        file_value = effect.get("file") or effect.get("path")
        if not file_value:
            raise StudioError(f"audio.sfx[{index}] requires a file")
        effect["file"] = str(_resolve_asset(str(file_value), brand_root, root))
        resolved_sfx.append(effect)
    if resolved_sfx:
        audio["sfx"] = resolved_sfx
    asset_manager = AssetManager(root, brand) if brand else None
    if asset_manager is not None:
        warnings.extend({"code": "asset", "message": message}
                        for message in asset_manager.warnings)
    # Narration cues: only from a real transcript with measured timestamps.
    cue_plan = None
    transcript = audio.get("transcript") or data.get("transcript")
    if transcript:
        transcript_path = _resolve_asset(str(transcript), brand_root, root)
        words = load_transcript(transcript_path)
        cue_plan = plan_cues(
            scenes, words,
            source="subtitle-cue" if transcript_path.suffix.lower() in (".srt", ".vtt")
            else "word-timestamps")
        scenes = apply_cue_plan(scenes, cue_plan)
    elif audio.get("voiceover"):
        warnings.append({
            "code": "unverified_audio_sync",
            "message": ("Voiceover is configured without a timestamped "
                        "transcript; cue timing remains editor-defined and is "
                        "not guaranteed to match spoken words."),
        })
    # Resolve scene media; videos become a deterministic still + camera move.
    still_cache: dict[tuple, Path] = {}
    for index, scene in enumerate(scenes):
        for media in scene.get("editorial_media") or []:
            if not isinstance(media, dict) or not media.get("asset"):
                raise StudioError("editorial_media items require asset paths")
            source = _resolve_asset(str(media["asset"]), brand_root, root)
            if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                raise StudioError("editorial_media currently supports still images only")
            if not source.is_file():
                raise StudioError(f"Missing editorial_media asset: {source}")
            media["asset"] = str(source)
        photo = scene.get("photo")
        background = scene.get("background")
        asset_value = photo or (background.get("asset")
                                if isinstance(background, dict) else None)
        if not asset_value:
            continue
        source = _resolve_asset(str(asset_value), brand_root, root)
        if source.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
            if asset_manager is None:
                raise StudioError("Video backgrounds require a brand asset manager")
            from .assets.manager import Asset
            asset = next((item for item in asset_manager.assets
                          if item.path.resolve() == source), None)
            if asset is None:
                asset = Asset(path=source, kind="video",
                              relative=source.name,
                              size_bytes=source.stat().st_size)
            time_value = float(scene.get("photo_time", 0))
            key = (source, time_value)
            if key not in still_cache:
                still_cache[key] = asset_manager.still(asset, time_value,
                                                       width=width)
            still = str(still_cache[key])
            scene["photo_source"] = str(source)
            if photo:
                scene["photo"] = still
            if isinstance(background, dict) and background.get("asset"):
                background = dict(background)
                background["asset"] = still
                background["video_source"] = str(source)
                scene["background"] = background
        else:
            if photo:
                scene["photo"] = str(source)
            if isinstance(background, dict) and background.get("asset"):
                background = dict(background)
                background["asset"] = str(source)
                scene["background"] = background
    project = StudioProject(
        path=path, root=root, name=str(data.get("name") or path.stem),
        width=width, height=height, fps=fps, style=style, scenes=scenes,
        brand=brand, brand_data=brand_data, audio=audio, export=export,
        tokens=tokens, fonts=fonts, asset_manager=asset_manager,
        cue_plan=cue_plan, warnings=warnings)
    return project


KINETIC_TYPES = {
    "amount", "breakdown", "announcement", "donut", "comparison",
    "heat", "europe", "deadline", "urgency", "cta",
}


def load_kinetic_studio(path: str | Path, *,
                        root: str | Path | None = None
                        ) -> tuple[StudioProject, Path | None]:
    """Adapt the legacy kinetic manifest into the shared studio engine.

    The existing Cairo implementation remains the default compatibility
    renderer. This opt-in bridge keeps its manifest fields while routing scene
    construction, layout, choreography, QA and export through the studio.
    """
    path = Path(path).resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StudioError(f"Cannot read kinetic manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise StudioError("Kinetic manifest must be a JSON object")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise StudioError("Kinetic manifest requires a nonempty scenes list")
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or scene.get("type") not in KINETIC_TYPES:
            raise StudioError(
                f"Kinetic scene {index + 1} has an unsupported legacy type")
        if "duration" not in scene:
            raise StudioError(f"Kinetic scene {index + 1} requires duration")

    if root is None:
        if "brands" in path.parts:
            position = path.parts.index("brands")
            root = Path(*path.parts[:position]) if position else Path("/")
        else:
            root = Path.cwd()
    root = Path(root).resolve()
    identity = data.get("identity") or {}
    if not isinstance(identity, dict):
        raise StudioError("Kinetic identity must be an object")
    video = dict(data.get("video") or {})
    video.setdefault("width", 720)
    video.setdefault("height", 1280)
    video.setdefault("fps", 25)
    audio: dict = {}
    voice = data.get("voiceover")
    if voice:
        audio["voiceover"] = {"file": voice} if isinstance(voice, str) else dict(voice)
    music = data.get("music")
    if music:
        music_config = {"file": music, "volume": .22} if isinstance(music, str) \
            else dict(music)
        music_config.setdefault("volume", .22)
        music_config.setdefault("ducking", "sidechain" if voice else "off")
        audio["music"] = music_config
    if data.get("transcript"):
        audio["transcript"] = data["transcript"]

    adapted_scenes = [dict(scene) for scene in scenes]
    warnings = [{
        "code": "legacy_kinetic_restyle",
        "message": ("Studio renderer uses the shared modern layout and motion "
                    "system; exact Cairo-frame parity is not guaranteed. "
                    "Legacy global header/logo placement may need per-scene review."),
    }]
    logo = data.get("logo")
    if logo:
        cta_scenes = [scene for scene in adapted_scenes
                      if scene.get("type") == "cta"]
        for scene in cta_scenes:
            scene.setdefault("logo", logo)
        warnings.append({
            "code": "legacy_logo_restyle",
            "message": ("The legacy kinetic header repeated its logo on every "
                        "scene; the studio adapter places it on CTA scenes only."),
        })
        if not cta_scenes:
            warnings.append({
                "code": "legacy_logo_placement_review",
                "message": ("Legacy kinetic header logos do not map to every "
                            "studio scene; add an explicit scene logo after review."),
            })

    overrides = {}
    if identity.get("accent"):
        overrides["palette"] = {"accent": identity["accent"]}
    adapted = {
        "name": data.get("name") or path.stem,
        "brand": data.get("brand"),
        "style": data.get("style") or "kinetic-advertising",
        "video": video,
        "scenes": adapted_scenes,
        "audio": audio,
        "export": {"codec": "libx264", "crf": 20, "preset": "veryfast"},
        "design_overrides": overrides,
        "_initial_warnings": warnings,
    }
    if not adapted["brand"]:
        adapted.pop("brand")
    project = _load_studio_data(path, adapted, root=root)
    legacy_output = data.get("output")
    if legacy_output:
        target = Path(legacy_output)
        legacy_output_path = target.resolve() if target.is_absolute() else (root / target).resolve()
    else:
        legacy_output_path = None
    return project, legacy_output_path


def resolve_render_size(project: StudioProject, profile: str | None) -> tuple[int, int, int]:
    if not profile:
        return project.width, project.height, project.fps
    if profile not in PROFILES:
        raise StudioError(f"Unknown export profile {profile!r}")
    spec = PROFILES[profile]
    return spec["width"], spec["height"], spec["fps"]
