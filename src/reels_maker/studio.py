"""High-level studio project loader.

A studio manifest is a superset of the legacy kinetic manifest. It resolves a
brand, a visual style, narration cues and export profile once, then exposes
immutable tokens and built scenes to the renderer and QA.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Mapping

from .assets.manager import AssetManager
from .audiokit.cues import apply_cue_plan, load_transcript, plan_cues
from .core.timeline import build_timeline
from .design.styles import canonical_style
from .design.tokens import resolve_tokens
from .textkit.typesetter import FontBook
from .studio_project import StudioProject


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
    if value.startswith("shared://"):
        shared_path = value.removeprefix("shared://")
        relative = PurePosixPath(shared_path)
        if (not shared_path or relative.is_absolute() or "\\" in shared_path
                or any(part in ("", ".", "..") for part in relative.parts)):
            raise StudioError(f"Invalid shared asset path: {value!r}")
        shared_root = (root / "shared_media").resolve()
        candidate = shared_root.joinpath(*relative.parts)
        resolved = candidate.resolve()
        try:
            resolved.relative_to(shared_root)
        except ValueError as exc:
            raise StudioError(
                f"Shared asset path escapes shared_media: {value!r}") from exc
    else:
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
        carousel = scene.get("carousel")
        if carousel is not None:
            if not isinstance(carousel, dict):
                raise StudioError(f"scenes[{index}].carousel must be an object")
            items = carousel.get("items")
            if not isinstance(items, list):
                raise StudioError(f"scenes[{index}].carousel.items must be an array")
            resolved_items = []
            for item_index, item in enumerate(items):
                if not isinstance(item, dict) or not item.get("image"):
                    raise StudioError(
                        f"scenes[{index}].carousel.items[{item_index}] requires an image")
                item = dict(item)
                source = _resolve_asset(str(item["image"]), brand_root, root)
                if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                    raise StudioError(
                        "photo-carousel currently supports PNG, JPEG or WebP stills only")
                item["image"] = str(source)
                resolved_items.append(item)
            scene["carousel"] = {**carousel, "items": resolved_items}
        video_layer = scene.get("video_layer")
        if video_layer is not None:
            if not isinstance(video_layer, dict) or not video_layer.get("path"):
                raise StudioError(
                    f"Scene {index + 1}: video_layer must be an object with a path")
            video_layer = dict(video_layer)
            source = _resolve_asset(str(video_layer["path"]), brand_root, root)
            if source.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm",
                                             ".avi", ".m4v"):
                raise StudioError(
                    f"Scene {index + 1}: video_layer requires a supported video file")
            video_layer["path"] = str(source)
            scene["video_layer"] = video_layer
        camera_canvas = scene.get("camera_canvas")
        if camera_canvas is not None:
            if not isinstance(camera_canvas, dict):
                raise StudioError(
                    f"Scene {index + 1}: camera_canvas must be an object")
            camera_video = scene.get("video")
            if camera_video:
                source = _resolve_asset(str(camera_video), brand_root, root)
                if source.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm",
                                                 ".avi", ".m4v"):
                    raise StudioError(
                        f"Scene {index + 1}: camera_canvas video requires a supported video file")
                scene["video"] = str(source)
        for media in scene.get("editorial_media") or []:
            if not isinstance(media, dict) or not media.get("asset"):
                raise StudioError("editorial_media items require asset paths")
            source = _resolve_asset(str(media["asset"]), brand_root, root)
            if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                raise StudioError("editorial_media currently supports still images only")
            if not source.is_file():
                raise StudioError(f"Missing editorial_media asset: {source}")
            media["asset"] = str(source)
        burst = scene.get("polaroid_burst")
        if burst is not None:
            if not isinstance(burst, dict):
                raise StudioError("polaroid_burst must be an object")
            burst = dict(burst)
            photos = burst.get("photos")
            if not isinstance(photos, list):
                raise StudioError("polaroid_burst.photos must be an array")
            resolved_photos = []
            for photo in photos:
                source = _resolve_asset(str(photo), brand_root, root)
                if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                    raise StudioError(
                        "polaroid_burst.photos currently supports still images only")
                resolved_photos.append(str(source))
            burst["photos"] = resolved_photos
            sound = burst.get("shutter_sound")
            if sound:
                burst["shutter_sound"] = str(
                    _resolve_asset(str(sound), brand_root, root))
            scene["polaroid_burst"] = burst
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
    # A Polaroid scene uses the same frame-quantized shot plan for its image
    # flashes and shutter clicks. Store generated clicks as ordinary SFX tracks
    # so the existing mixer, AAC export and output probe handle them unchanged.
    shutter_events = []
    polaroid_timeline = build_timeline(scenes, fps)
    for index, scene in enumerate(scenes):
        burst = scene.get("polaroid_burst")
        if not isinstance(burst, dict) or not burst.get("shutter_sound"):
            continue
        from .motionkit.polaroid_burst import plan_polaroid_burst
        timing = polaroid_timeline.scenes[index]
        shots = plan_polaroid_burst(
            burst, width, height, timing.duration, fps,
            fallback_seed=index * 17 + 3)
        gain_db = burst.get("shutter_gain_db", -10)
        if isinstance(gain_db, bool) or not isinstance(gain_db, (int, float)):
            raise StudioError("polaroid_burst.shutter_gain_db must be numeric")
        for shot in shots:
            shutter_events.append({
                "file": burst["shutter_sound"],
                "time": round((timing.start_frame + shot.flash_frame) / fps, 6),
                "gain_db": float(gain_db),
                "source": "polaroid_burst",
            })
    if shutter_events:
        audio.setdefault("sfx", []).extend(shutter_events)
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
