#!/usr/bin/env python3
"""Generate the kia-nowicki KILLER3 reel manifest v2 (karaoke captions burned
into per-file media by _build_killer3_captions.py; manifest only cuts).

Timeline v2.1:
  0.0-4.3   killer3_intro_punch_cap  (punch-in: manager entering the door,
            meme label "*wchodzi kierownik*"; ends exactly at the source's
            own cut, so the next shot is already full-frame)
  4.3-54.7  killer3_graded_cap       (wide shots + karaoke captions)
  54.7-57.9 punch1_couch_cap         (punch-in: Wąsik on the couch)
  57.9-87.9 killer3_master_cap
  87.9-91.9 punch2_couch_cap         (punch-in: Wąsik)
  91.9-93.4 killer3_master_cap       (whip pan to the desk)
  93.4-100.4 punch3_desk_cap         (punch-in: Wąsik at the desk, CTA)
  100.4-102.7 killer3_outro_fade     (fade to white)
  102.7-110.7 drone_white_cap        (fade from white, drone in motion,
            teleadresowa voiceover + captions)
Total: 110.7s
"""
import json

DRONE_START = 101.00
VOICEOVER_OFFSET = 101.60

SCENES = [
    ("imports/footage/killer3_intro_punch_cap.mp4", 0.0, 4.3),
    ("imports/footage/killer3_graded_cap.mp4", 4.3, 50.4),
    ("imports/footage/punch1_couch_cap.mp4", 0.0, 3.2),
    ("imports/footage/killer3_graded_cap.mp4", 57.9, 30.0),
    ("imports/footage/punch2_couch_cap.mp4", 0.0, 4.0),
    ("imports/footage/killer3_graded_cap.mp4", 91.9, 1.5),
    ("imports/footage/punch3_desk_cap.mp4", 0.0, 6.5),
    ("imports/footage/killer3_outro_fade.mp4", 0.0, 1.1),
    ("imports/footage/drone_white_cap.mp4", 0.0, 8.0),
]

manifest = {
    "name": "kia-nowicki-killer3-reel",
    "brand": "kia-nowicki",
    "video": {"width": 1080, "height": 1920, "fps": 30},
    "output": "renders/kia-nowicki/kia-nowicki-killer3-reel.mp4",
    "music": {
        "file": "imports/audio/killer3_dialog_padded.m4a",
        "start": 0.0,
        "volume": 1.0,
        "fade_out": 0.0
    },
    "voiceover": {
        "file": "imports/audio/nowicki-kalisz-radio-dogrywka-teleadresowa.wav",
        "start": 0.0,
        "offset_seconds": VOICEOVER_OFFSET,
        "volume": 0.6
    },
    "scenes": [
        {"file": f, "start": round(s, 3), "duration": round(d, 3)}
        for f, s, d in SCENES
    ],
}

path = "brands/kia-nowicki/projects/kia-nowicki-killer3-reel.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
    f.write("\n")
total = sum(d for _, _, d in SCENES)
print(f"wrote {path}: {len(SCENES)} scenes, total {total}s")
