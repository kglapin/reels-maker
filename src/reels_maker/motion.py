"""Non-gimmicky per-element animation using FFmpeg alpha and overlay filters.

Each title field and logo is a separate cropped transparent layer. The scene
background is rendered once; layers gain opacity independently and slide a few
pixels into their final positions with ease-out, without any bounce or zoom.
"""
from __future__ import annotations

from .ffmpeg import RenderError


def compose_motion(vf: str, fps: int, scene_frames: int, background,
                   layers: list[dict], settings: dict, width: int) -> list[str]:
    """Return FFmpeg input and filter arguments for an editorial reveal."""
    duration = settings.get("duration_frames", max(2, round(fps * .24)))
    stagger = settings.get("stagger_frames", max(1, round(fps * .07)))
    preset = settings["preset"]
    movement = (0 if preset == "fade_stagger" else
                round(settings.get("distance_px", 28) * width / 1080))
    # Decoration and branding should not postpone the actual message.
    # A headline with several styled runs enters in reading order; supporting
    # text comes afterwards. This scheduling does not change z-order.
    active = [x for x in layers if x.get("role") not in ("logo", "accent")]
    slots = {id(layer): index for index, layer in enumerate(active)}
    latest_slot = max((slots.get(id(layer), 0) for layer in layers), default=0)
    # Keep a meaningful static reading window after all entrances finish.
    min_hold = max(1, round(.55 * fps))
    if duration + stagger * latest_slot + min_hold > scene_frames:
        raise RenderError(
            "Motion leaves too little reading time (minimum 0.55s static hold); "
            "shorten the animation or simplify the title")
    args = ["-loop", "1", "-framerate", str(fps), "-i", str(background)]
    graph = [f"[0:v]{vf}[base]",
             "[1:v]format=rgba[background]",
             "[base][background]overlay=x=0:y=0:shortest=1[step0]"]
    for index, layer in enumerate(layers):
        args += ["-loop", "1", "-framerate", str(fps), "-i", layer["file"]]
        # Alpha fade and a modest vertical translation, both opt-in.
        delay = slots.get(id(layer), 0) * stagger / fps
        seconds = duration / fps
        # FFmpeg overlay evaluates y on each frame. Escape commas in expressions.
        progress = (
            f"pow(max(0\\,1-min(1\\,(t-{delay:.8f})/{seconds:.8f}))\\,3)"
        )
        x_offset, y_offset = str(layer["x"]), str(layer["y"])
        if movement and preset in ("editorial_reveal", "rise_soft"):
            y_offset = f"{layer['y']}+{movement}*{progress}"
        elif movement and preset in ("slide_left", "slide_right"):
            sign = -1 if preset == "slide_left" else 1
            x_offset = f"{layer['x']}+{sign * movement}*{progress}"
        graph.append(
            f"[{index+2}:v]format=rgba,"
            f"fade=t=in:st={delay:.8f}:d={seconds:.8f}:alpha=1[layer{index}]")
        graph.append(
            f"[step{index}][layer{index}]"
            f"overlay=x='{x_offset}':y='{y_offset}':"
            f"shortest=1:format=auto[step{index+1}]")
    graph.append(f"[step{len(layers)}]format=yuv420p[v]")
    args += ["-filter_complex", ";".join(graph), "-map", "[v]"]
    return args
