#!/usr/bin/env python3
"""Generate the kia-nowicki PITBULL reel manifest (v2 scheme from KILLER3:
manifest only cuts caption-burned media; audio = masked dialog on the music
track + teleadresowa voiceover over the drone outro).

Timeline (output time == graded-master source time):
   0.00-18.83  pitbull_graded_cap        (desk + phone call, karaoke captions)
  18.83-21.60  pitbull_punch1_table_cap  (punch-in: "to samo imię?")
  21.60-41.00  pitbull_graded_cap        (table + back-turned + chase)
  41.00-43.13  pitbull_punch2_neptun_cap (punch-in: Neptune line, beep-masked)
  43.13-45.90  pitbull_graded_cap        (showroom intro line)
  45.90-48.80  pitbull_punch3_price_cap  (punch-in: 109 900 XCeed)
  48.80-58.17  pitbull_graded_cap        (specs + closing)
  58.17-59.27  pitbull_outro_fade        (dip to white)
  59.27-67.27  drone_white_pitbull_cap   (fade from white, teleadresowa)
Total: 67.27s
"""
import json

DIP_START = 58.167
DRONE_START = 59.267
VOICEOVER_OFFSET = DRONE_START  # owner: lektor starts together with the drone clip

SCENES = [
    ("imports/footage/pitbull_graded_cap.mp4", 0.0, 18.833),
    ("imports/footage/pitbull_punch1_table_cap.mp4", 0.0, 2.767),
    ("imports/footage/pitbull_graded_cap.mp4", 21.60, 19.40),
    ("imports/footage/pitbull_punch2_neptun_cap.mp4", 0.0, 2.133),
    ("imports/footage/pitbull_graded_cap.mp4", 43.133, 2.767),
    ("imports/footage/pitbull_punch3_price_cap.mp4", 0.0, 2.90),
    ("imports/footage/pitbull_graded_cap.mp4", 48.80, 9.367),
    ("imports/footage/pitbull_outro_fade.mp4", 0.0, 1.10),
    ("imports/footage/drone_white_pitbull_cap.mp4", 0.0, 8.0),
]

manifest = {
    "name": "kia-nowicki-pitbull-reel",
    "brand": "kia-nowicki",
    "video": {"width": 1080, "height": 1920, "fps": 30},
    "output": "renders/kia-nowicki/kia-nowicki-pitbull-reel.mp4",
    "music": {
        "file": "imports/audio/pitbull_dialog_padded.m4a",
        "start": 0.0,
        "volume": 1.0,
        "fade_out": 0.5,
    },
    "voiceover": {
        "file": "imports/audio/nowicki-kalisz-radio-dogrywka-teleadresowa.wav",
        "start": 0.0,
        "offset_seconds": VOICEOVER_OFFSET,
        "volume": 0.6,
    },
    "scenes": [
        {"file": f, "start": round(s, 3), "duration": round(d, 3)}
        for f, s, d in SCENES
    ],
}

path = "brands/kia-nowicki/projects/kia-nowicki-pitbull-reel.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
    f.write("\n")
total = sum(d for _, _, d in SCENES)
print(f"wrote {path}: {len(SCENES)} scenes, total {total:.3f}s")
