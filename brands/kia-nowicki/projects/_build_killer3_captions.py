#!/usr/bin/env python3
"""Burn karaoke captions into prepared media via transparent PNG overlays.

Why not ASS: the local FFmpeg 8 builds ship without libass and without
drawtext, so captions are rendered with PIL (KiaDesignK Bold TTF, identical
to the engine's title pipeline) as per-frame RGBA overlays and composited
with FFmpeg's `overlay` filter.

Caption design (brands/kia-nowicki/BRAND.md v2):
- bold white text, dark soft outline/shadow;
- karaoke emphasis: words not yet spoken are muted grey, the currently spoken
  word turns bright white at its onset (per-frame redraw, 30 fps);
- per-caption y position keeps lines as close to the vertical centre as
  possible without ever covering a speaker's face (measured from QA frames).

Input: renders/kia-nowicki/qa/captions/captions.json
  [{"target": "file.mp4", "local_t0": s, "local_t1": s, "y": px, "static": bool,
    "words": [{"w": "word", "t": seconds_in_target_file}, ...]}, ...]
"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(".").resolve()
MEDIA = ROOT / "brands/kia-nowicki/imports/footage"
WORK = ROOT / "renders/kia-nowicki/qa/captions"
WORK.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
FPS = 30
FONT_SIZE = 58
FONT_PATH = ROOT / "brands/kia-nowicki/imports/fonts/KiaDesignK-Bold.ttf"
STROKE_WIDTH = 2
MAX_TEXT_WIDTH = W - 2 * 96  # brand safe area
COLOR_SPOKEN = (255, 255, 255, 255)
COLOR_PENDING = (176, 182, 190, 255)
OUTLINE = (16, 15, 15, 255)
SHADOW = (0, 0, 0, 110)

_font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
LINE_STEP = int(FONT_SIZE * 1.24)


def caption_layout(cap):
    """Wrap words into lines; returns list of lines, each [(word, x_offset, width)].

    A word whose text ends with '\\n' forces a line break after it.
    """
    space_w = _font.getlength(" ")
    lines, current, widths = [], [], []
    for word in cap["words"]:
        text = word["w"]
        forced = text.endswith("\n")
        if forced:
            text = text[:-1]
        w_width = _font.getlength(text)
        candidate = sum(widths) + space_w * len(widths) + w_width
        if current and candidate > MAX_TEXT_WIDTH:
            lines.append(current)
            current, widths = [], []
        current.append((word, w_width, text))
        widths.append(w_width)
        if forced:
            # break only AFTER this word, never before it
            lines.append(current)
            current, widths = [], []
    if current:
        lines.append(current)
    return lines


def _car_band(car_specs):
    """Load and scale car cutouts; returns ([(spec, im)], total_w, target_h, gap)."""
    imgs = []
    target_h = 160
    brand = ROOT / "brands/kia-nowicki"
    for spec in car_specs:
        p = spec["path"]
        path = p if p.startswith("brands/") else (brand / p)
        im = Image.open(path).convert("RGBA")
        scale = target_h / im.height
        im = im.resize((max(1, round(im.width * scale)), target_h), Image.LANCZOS)
        imgs.append((spec, im))
    gap = 48
    total_w = sum(im.width for _, im in imgs) + gap * (len(imgs) - 1)
    return imgs, total_w, target_h, gap


def _car_state(spec, t):
    """Sequential entrance/exit animation state: None | (alpha, y_offset).

    Entrance: fade in + rise (ease-out, 0.25s) at the model's spoken onset.
    Exit: fade out + rise (ease-out, 0.25s) ending at spec['t_out'].
    """
    t_in, t_out = spec["t_in"], spec["t_out"]
    fade = 0.25
    if t < t_in - 1e-6 or t > t_out + 1e-6:
        return None
    alpha, offset = 1.0, 0.0
    dt = t - t_in
    if dt < fade:
        p = max(0.0, dt / fade)
        p = 1 - (1 - p) ** 3  # ease-out cubic
        alpha = p
        offset = (1 - p) * 28
    dt2 = t_out - t
    if dt2 < fade:
        p = max(0.0, dt2 / fade)
        p = 1 - (1 - p) ** 3
        alpha = min(alpha, p)
        offset = max(offset, (1 - p) * 28)
    return alpha, int(round(offset))


COUNTDOWN_FONT = ROOT / "brands/kia-nowicki/imports/fonts/KiaDesignK-Bold.ttf"
_font_cache = {}


def _big_font(size: int):
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(str(COUNTDOWN_FONT), size)
    return _font_cache[size]


def render_countdown(cap, t, img):
    """Big 3/2/1 numerals centred on screen with a pop-in and blurred shadow."""
    for item in cap.get("countdown") or []:
        t0, t1 = item["t0"], item["t1"]
        if not (t0 - 1e-6 <= t <= t1 + 1e-6):
            continue
        p = min(1.0, (t - t0) / max(0.01, (t1 - t0)))
        pop = 1.0 + 0.14 * max(0.0, 1 - p * 3)  # settles to 1.0 quickly
        alpha = min(1.0, max(0.0, (t - t0) / 0.12))
        size = int(340 * pop)
        font = _big_font(size)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        s = ImageDraw.Draw(shadow)
        num = item["n"]
        bbox = d.textbbox((0, 0), num, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = W / 2 - tw / 2 - bbox[0], 900 - th / 2 - bbox[1]
        s.text((x + 6, y + 10), num, font=font, fill=(0, 0, 0, 150),
               stroke_width=6, stroke_fill=(0, 0, 0, 150))
        d.text((x, y), num, font=font, fill=(255, 255, 255, int(255 * alpha)),
               stroke_width=6, stroke_fill=OUTLINE)
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        shadow.putalpha(shadow.getchannel("A").point(
            lambda v: int(v * alpha * 0.7)))
        layer.putalpha(layer.getchannel("A").point(
            lambda v: int(v * alpha)))
        img = Image.alpha_composite(img, shadow)
        img = Image.alpha_composite(img, layer)
    return img


def render_frame(cap, lines, t, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # --- car photos band (upper part, sequential fade/rise in and out) ---
    car_specs = cap.get("photos") or []
    if car_specs:
        cars, total_w, car_h, gap = _car_band(car_specs)
        x0 = (W - total_w) / 2
        band_bottom = 540
        ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(ground)
        x = x0
        for spec, im in cars:
            state = _car_state(spec, t)
            if state:
                alpha, dy = state
                gdraw.ellipse(
                    [x + 10, band_bottom - 16, x + im.width - 10, band_bottom + 8],
                    fill=(0, 0, 0, int(130 * alpha)))
            x += im.width + gap
        ground = ground.filter(ImageFilter.GaussianBlur(12))
        img = Image.alpha_composite(img, ground)
        x = x0
        for spec, im in cars:
            state = _car_state(spec, t)
            if state:
                alpha, dy = state
                layer = im.copy()
                layer.putalpha(layer.getchannel("A").point(
                    lambda v: int(v * alpha)))
                img.alpha_composite(
                    layer, (round(x), band_bottom - im.height + dy))
            x += im.width + gap

    # --- text layer with a strongly blurred drop shadow for readability ---
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    sdraw = ImageDraw.Draw(shadow_layer)
    space_w = _font.getlength(" ")
    block_h = LINE_STEP * len(lines)
    top = cap["y"] - block_h // 2
    show_text = cap.get("show_text", True)
    for line in lines:
        if not show_text:
            break
        line_w = sum(w for _, w, _ in line) + space_w * (len(line) - 1)
        x = (W - line_w) / 2
        baseline = top + (LINE_STEP - FONT_SIZE) // 2
        for word, w_width, text in line:
            spoken = (cap["static"] or t >= word["t"])
            color = COLOR_SPOKEN if spoken else COLOR_PENDING
            sdraw.text((x + 3, baseline + 7), text, font=_font,
                       fill=(0, 0, 0, 150), stroke_width=STROKE_WIDTH + 2,
                       stroke_fill=(0, 0, 0, 150))
            draw.text((x, baseline), text, font=_font, fill=color,
                      stroke_width=STROKE_WIDTH, stroke_fill=OUTLINE)
            x += w_width + space_w
        top += LINE_STEP
    shadow_blur = shadow_layer.filter(ImageFilter.GaussianBlur(9))
    shadow_blur.putalpha(shadow_blur.getchannel("A").point(lambda v: v * 70 // 100))
    img = Image.alpha_composite(img, shadow_blur)
    img = Image.alpha_composite(img, text_layer)
    img = render_countdown(cap, t, img)
    img.save(path, compress_level=3)


def build_overlay(target: str, caps):
    src = MEDIA / target
    out = MEDIA / target.replace(".mp4", "_cap.mp4")
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
        capture_output=True, text=True, check=True).stdout.strip())
    n_frames = int(duration * FPS + 0.5)
    frames_dir = WORK / ("frames_" + target.replace(".mp4", ""))
    if frames_dir.exists():
        import shutil
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()
    layouts = [(cap, caption_layout(cap)) for cap in caps]
    for i in range(n_frames):
        t = i / FPS
        active = None
        active_lines = None
        for cap, lines in layouts:
            in_caption = cap["local_t0"] - 1e-6 <= t <= cap["local_t1"] + 1e-6
            in_cars = any(
                spec["t_in"] - 1e-6 <= t <= spec["t_out"] + 1e-6
                for spec in (cap.get("photos") or []))
            in_countdown = any(
                item["t0"] - 1e-6 <= t <= item["t1"] + 1e-6
                for item in (cap.get("countdown") or []))
            if in_caption or in_cars or in_countdown:
                active, active_lines = cap, lines
                active["show_text"] = in_caption
        frame_path = frames_dir / f"cap_{i:05d}.png"
        if active is None:
            # cheap fully transparent placeholder only when missing
            if not frame_path.exists():
                Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(
                    frame_path, compress_level=3)
        else:
            render_frame(active, active_lines, t, frame_path)
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-framerate", str(FPS), "-i", str(frames_dir / "cap_%05d.png"),
        "-filter_complex",
        f"[0:v][1:v]overlay=format=auto:eof_action=pass[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-c:a", "copy", str(out),
    ], check=True)
    print(f"burned {out.name} ({n_frames} frames)")


def main():
    caps = json.loads((WORK / "captions.json").read_text(encoding="utf-8"))
    for cap in caps:
        cap.setdefault("static", False)
    per_file = {}
    for cap in caps:
        per_file.setdefault(cap["target"], []).append(cap)
    for target, file_caps in per_file.items():
        build_overlay(target, file_caps)


if __name__ == "__main__":
    main()
