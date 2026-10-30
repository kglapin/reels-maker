#!/usr/bin/env python3
"""Build PITBULL reel media from the graded master (brands/kia-nowicki).

Produces:
- imports/footage/pitbull_punch1_table.mp4   18.84-21.60  (Zbyszek: "to samo imię?")
- imports/footage/pitbull_punch2_neptun.mp4  41.00-43.13  ("Czy tam, kurwa, Neptun?")
- imports/footage/pitbull_punch3_price.mp4   45.90-48.80  (price: 109 900 XCeed)
- imports/footage/pitbull_outro_fade.mp4     58.17-59.27  (dip to white)

Punch-ins follow BRAND.md: crop back to a talking speaker only, 1.5x
(720x1280 crop scaled back to 1080x1920).
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOOT = ROOT / "brands/kia-nowicki/imports/footage"
MASTER = FOOT / "pitbull_graded.mp4"

W, H = 1080, 1920
CW, CH = 720, 1280  # 1.5x punch

# name: (source_start, duration, centre_x, centre_y)
PUNCHES = {
    "pitbull_punch1_table.mp4": (18.84, 2.76, 720, 700),
    "pitbull_punch2_neptun.mp4": (41.00, 2.13, 760, 660),
    "pitbull_punch3_price.mp4": (45.90, 2.90, 700, 760),
}


def clamp_center(cx, cy):
    return (
        min(max(cx, CW // 2), W - CW // 2),
        min(max(cy, CH // 2), H - CH // 2),
    )


def run(cmd):
    subprocess.run(cmd, check=True, cwd=ROOT)


for name, (start, dur, cx, cy) in PUNCHES.items():
    cx, cy = clamp_center(cx, cy)
    x, y = cx - CW // 2, cy - CH // 2
    out = FOOT / name
    run([
        "ffmpeg", "-v", "error", "-y",
        "-ss", str(start), "-t", str(dur), "-i", str(MASTER),
        "-vf", f"crop={CW}:{CH}:{x}:{y},scale={W}:{H}:flags=lanczos",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-c:a", "copy", str(out),
    ])
    print(f"punch {name} <- {start}+{dur} crop {CW}x{CH}@{x},{y}")

# dip-to-white tail from the graded master (audio stays on the music track)
out = FOOT / "pitbull_outro_fade.mp4"
run([
    "ffmpeg", "-v", "error", "-y",
    "-ss", "58.17", "-t", "1.10", "-i", str(MASTER),
    "-vf", "fade=t=out:st=0.10:d=1.00:color=white",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16",
    "-pix_fmt", "yuv420p", "-c:a", "copy", str(out),
])
print("outro pitbull_outro_fade.mp4 <- 58.17+1.10 fade to white")

# drone outro: trim the first second (owner request) so the camera is already
# moving toward the building on the first visible frame; short 0.3s fade from
# white keeps the dip transition but shows motion immediately.
out = FOOT / "drone_white_pitbull.mp4"
run([
    "ffmpeg", "-v", "error", "-y",
    "-ss", "1.0", "-t", "8.0", "-i", str(FOOT / "dron_graded_vertical.mp4"),
    "-vf", "fade=t=in:st=0:d=0.30:color=white",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16",
    "-pix_fmt", "yuv420p", "-an", str(out),
])
print("outro drone_white_pitbull.mp4 <- source 1.0+8.0, 0.3s fade from white")
