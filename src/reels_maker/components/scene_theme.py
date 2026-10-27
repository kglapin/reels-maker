"""Scene-level palette interpretation and background specifications."""
from __future__ import annotations

from ..design.color import (
    darken, ensure_contrast, lighten, mix, parse_hex, relative_luminance,
)
from .model import SceneContext


def theme_for_scene(ctx: SceneContext, scene: dict) -> dict:
    palette = ctx.tokens.palette
    background = scene.get("background") or {}
    kind = background.get("kind") if isinstance(background, dict) else None
    if kind == "solid":
        base = parse_hex(background.get("color", "#101A14"))
    elif kind == "gradient":
        base = parse_hex(background.get("from", background.get("color", "#101A14")))
    elif scene.get("photo") or (isinstance(background, dict)
                                 and background.get("asset")):
        base = (14, 22, 17)
    else:
        base = palette.background
    light = relative_luminance(base) > .46
    if scene.get("theme") == "light":
        light = True
    elif scene.get("theme") == "dark":
        light = False
    photo = bool(scene.get("photo") or (isinstance(background, dict)
                                         and background.get("asset")))
    if light:
        ink = darken(base, .88) if relative_luminance(base) > .25 else (18, 30, 22)
        muted = mix(ink, base, .38)
        accent = ensure_contrast(palette.accent, base, 4.5)
        surface = palette.surface if relative_luminance(palette.surface) > .7 else (255, 255, 255)
        kicker = accent
        scrim = 0.0
    else:
        ink = (255, 255, 255)
        muted = lighten(ink, .22)
        accent = ensure_contrast(palette.accent, base, 4.5)
        surface = palette.surface
        kicker = ink if photo else accent
        scrim = .62 if photo else (.55 if ctx.tokens.backdrop != "none" else .15)
    return {"light": light, "base": base, "ink": ink, "muted": muted,
            "accent": accent, "kicker": kicker, "surface": surface,
            "scrim": scrim, "photo": photo}


def background_for_scene(ctx: SceneContext, scene: dict, theme: dict) -> dict:
    palette = ctx.tokens.palette
    config = scene.get("background")
    if not isinstance(config, dict):
        config = {}
    photo = scene.get("photo") or config.get("asset") or config.get("photo")
    if photo:
        camera = config.get("camera") or scene.get("camera") or {}
        if isinstance(camera, str):
            camera = {"direction": camera}
        return {
            "kind": "photo",
            "asset": photo,
            "video_source": scene.get("photo_source") or config.get("video_source"),
            "time": scene.get("photo_time", config.get("time", 0)),
            "camera": {
                "direction": camera.get("direction", "push-in"),
                "intensity": camera.get("intensity", ctx.tokens.motion.camera_drift),
            },
            "scrim": config.get("scrim", theme["scrim"]),
            "tint": config.get("tint"),
            "blur": config.get("blur", 0),
        }
    kind = config.get("kind", "gradient" if not theme["light"] else "solid")
    if kind == "solid":
        return {"kind": "solid", "color": config.get("color", theme["base"])}
    start = config.get("from", theme["base"])
    end = config.get("to", mix(theme["base"], theme["accent"],
                               .10 if not theme["light"] else .04))
    return {"kind": "gradient", "from": start, "to": end,
            "angle": config.get("angle", 90)}


def is_light_scene(ctx: SceneContext, scene: dict) -> bool:
    return theme_for_scene(ctx, scene)["light"]
