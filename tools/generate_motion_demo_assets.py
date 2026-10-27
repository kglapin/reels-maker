#!/usr/bin/env python3
"""Generate original, synthetic stills and video for the Motion Lab demo.

No network access or third-party media is used. Images are designed
illustrations (not photographs) and the short clips are generated frame by
frame with Pillow before H.264 encoding through FFmpeg.
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT = 720, 1280
FPS = 30
DURATION = 12
ACCENT = (66, 214, 164)
CYAN = (78, 192, 246)
INK = (8, 16, 30)


def gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        color = tuple(round(a * (1 - t) + b * t) for a, b in zip(top, bottom))
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def solar_field() -> Image.Image:
    image = gradient((78, 150, 188), (225, 205, 155))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((475, 120, 635, 280), fill=(255, 229, 158, 210))
    draw.polygon([(0, 650), (250, 495), (500, 625), (720, 480),
                  (720, 1280), (0, 1280)], fill=(68, 112, 78, 255))
    for row in range(7):
        y = 625 + row * 96
        shift = row * 30
        for col in range(-1, 5):
            x = col * 180 - shift
            pts = [(x, y), (x + 150, y - 28), (x + 192, y + 37),
                   (x + 37, y + 65)]
            draw.polygon(pts, fill=(18, 44, 74, 245),
                         outline=(112, 174, 205, 220), width=3)
            for line in range(1, 5):
                px = x + line * 30
                draw.line((px, y - line * 6, px + 37, y + 59 - line * 6),
                          fill=(120, 177, 201, 120), width=2)
    return image.filter(ImageFilter.GaussianBlur(.25))


def battery_room() -> Image.Image:
    image = gradient((13, 26, 41), (31, 52, 62))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 1000, WIDTH, HEIGHT), fill=(9, 18, 28, 255))
    for row in range(3):
        y = 260 + row * 270
        for col in range(4):
            x = 45 + col * 165
            draw.rounded_rectangle((x, y, x + 132, y + 222), radius=12,
                                   fill=(30, 47, 61, 255),
                                   outline=(91, 117, 130, 255), width=4)
            draw.rectangle((x + 16, y + 25, x + 116, y + 54),
                           fill=(54, 75, 88, 255))
            draw.rounded_rectangle((x + 48, y + 90, x + 87, y + 169),
                                   radius=8, fill=(*ACCENT, 235))
            draw.ellipse((x + 96, y + 92, x + 109, y + 105),
                         fill=(120, 243, 180, 255))
    return image


def wind_farm() -> Image.Image:
    image = gradient((45, 110, 160), (242, 183, 115))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((510, 170, 660, 320), fill=(255, 220, 150, 220))
    draw.polygon([(0, 785), (180, 645), (380, 740), (590, 610),
                  (720, 700), (720, HEIGHT), (0, HEIGHT)],
                 fill=(44, 104, 80, 255))
    for cx, cy, scale in ((155, 555, 1.0), (445, 430, .82), (625, 610, .64)):
        hub = (cx, cy)
        draw.line((cx, cy, cx - 12 * scale, cy + 420 * scale),
                  fill=(231, 239, 235, 245), width=max(3, round(9 * scale)))
        for angle in (-90, 30, 150):
            rad = math.radians(angle)
            tip = (cx + math.cos(rad) * 225 * scale,
                   cy + math.sin(rad) * 225 * scale)
            mid = (cx + math.cos(rad + .12) * 50 * scale,
                   cy + math.sin(rad + .12) * 50 * scale)
            draw.polygon([hub, tip, mid], fill=(241, 246, 242, 240))
    return image


def city_grid() -> Image.Image:
    image = gradient((7, 15, 35), (30, 45, 68))
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(2901)
    x = -12
    while x < WIDTH:
        w = rng.randint(45, 115)
        top = rng.randint(390, 810)
        draw.rectangle((x, top, x + w, HEIGHT),
                       fill=(14, 26, 46, 255),
                       outline=(76, 102, 126, 180), width=2)
        for wy in range(top + 28, HEIGHT - 35, 42):
            for wx in range(x + 12, x + w - 8, 23):
                if rng.random() > .22:
                    color = (255, 210, 108, 205) if rng.random() > .45 else (*CYAN, 180)
                    draw.rectangle((wx, wy, wx + 8, wy + 15), fill=color)
        x += w + 8
    return image


def energy_frame(frame: int, variant: int) -> Image.Image:
    t = frame / (FPS * DURATION)
    image = gradient((8, 16, 30), (17, 40, 59))
    draw = ImageDraw.Draw(image, "RGBA")
    center = (WIDTH / 2, HEIGHT / 2)
    for ring in range(6):
        radius = 90 + ring * 75
        start = (t * 360 + ring * 27) % 360
        draw.arc((center[0] - radius, center[1] - radius,
                  center[0] + radius, center[1] + radius),
                 start=start, end=start + 230,
                 fill=(*((ACCENT if (ring + variant) % 2 else CYAN)),
                       max(50, 205 - ring * 18)), width=5 + ring % 2)
    for ray in range(12):
        angle = math.radians(ray * 30 + frame * (1 if variant else -1))
        inner = 35 + (frame * 7 + ray * 19) % 280
        outer = inner + 90 + (ray % 3) * 24
        p1 = (center[0] + math.cos(angle) * inner,
              center[1] + math.sin(angle) * inner)
        p2 = (center[0] + math.cos(angle) * outer,
              center[1] + math.sin(angle) * outer)
        draw.line((p1, p2), fill=(*ACCENT, 165), width=3)
    draw.ellipse((center[0] - 18, center[1] - 18,
                  center[0] + 18, center[1] + 18), fill=(246, 252, 255, 255))
    return image


def write_video(path: Path, variant: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to generate demo video clips")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
               f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame in range(FPS * DURATION):
            process.stdin.write(energy_frame(frame, variant).tobytes())
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr else b""
        code = process.wait()
    except Exception:
        process.kill()
        process.wait()
        raise
    if code:
        raise RuntimeError(f"FFmpeg failed to generate {path}: "
                           f"{stderr.decode('utf-8', 'replace')[-2000:]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand-root", type=Path,
                        default=Path("brands/motion-lab"))
    args = parser.parse_args()
    output = args.brand_root / "media" / "stock"
    output.mkdir(parents=True, exist_ok=True)
    stills = {
        "solar-field-synthetic.png": solar_field(),
        "battery-room-synthetic.png": battery_room(),
        "wind-farm-synthetic.png": wind_farm(),
        "city-grid-synthetic.png": city_grid(),
    }
    for name, image in stills.items():
        image.save(output / name, optimize=True)
    write_video(output / "energy-orbit-synthetic.mp4", 0)
    write_video(output / "grid-flow-synthetic.mp4", 1)
    print(f"Generated {len(stills)} synthetic stills and 2 synthetic videos in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
