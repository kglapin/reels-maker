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
FONT_PATH = ROOT / "brands/kia-nowicki/imports/fonts/KiaDesignK-Regular.ttf"
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


def _car_band(car_paths):
    """Load, scale and bottom-align car cutouts; returns (list of RGBA, total_w, height)."""
    imgs = []
    target_h = 160
    brand = ROOT / "brands/kia-nowicki"
    for p in car_paths:
        path = p if p.startswith("brands/") else (brand / p)
        im = Image.open(path).convert("RGBA")
        scale = target_h / im.height
        im = im.resize((max(1, round(im.width * scale)), target_h), Image.LANCZOS)
        imgs.append(im)
    gap = 48
    total_w = sum(im.width for im in imgs) + gap * (len(imgs) - 1)
    return imgs, total_w, target_h, gap


def render_frame(cap, lines, t, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # --- car photos band (upper part of the frame, transparent cutouts) ---
    car_paths = cap.get("photos") or []
    if car_paths:
        imgs, total_w, car_h, gap = _car_band(car_paths)
        x = (W - total_w) / 2
        band_bottom = 620
        # soft blurred ground shadow under the cars
        ground = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(ground)
        for im in imgs:
            gdraw.ellipse(
                [x + 10, band_bottom - 16, x + im.width - 10, band_bottom + 8],
                fill=(0, 0, 0, 130))
            x += im.width + gap
        ground = ground.filter(ImageFilter.GaussianBlur(12))
        img = Image.alpha_composite(img, ground)
        x = (W - total_w) / 2
        for im in imgs:
            img.alpha_composite(im, (round(x), band_bottom - im.height))
            x += im.width + gap

    # --- text layer with a strongly blurred drop shadow for readability ---
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    sdraw = ImageDraw.Draw(shadow_layer)
    space_w = _font.getlength(" ")
    block_h = LINE_STEP * len(lines)
    top = cap["y"] - block_h // 2
    for line in lines:
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
            if cap["local_t0"] - 1e-6 <= t <= cap["local_t1"] + 1e-6:
                active, active_lines = cap, lines
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
