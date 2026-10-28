#!/usr/bin/env python3
"""Generate the kia-nowicki KILLER3 reel manifest.

Scene boundaries follow Whisper word timestamps (renders/kia-nowicki/qa/6_KILLER3.json).
Captions are per-scene title.body blocks per brands/kia-nowicki/BRAND.md.
Punch-in scenes reference pre-cropped segments from the graded master.
"""
import json

CAPTION = {"theme": "dark", "position": "lower", "backdrop": "soft",
           "logo": False, "accent_rule": False}

MASTER = "imports/footage/killer3_graded.mp4"
DRONE = "imports/footage/dron_graded_vertical.mp4"
P1 = "imports/footage/punch1_couch.mp4"
P2 = "imports/footage/punch2_couch.mp4"
P3 = "imports/footage/punch3_desk.mp4"

# (start, end, caption or None, file override or None, source_start for punch files)
TIMELINE = [
    (0.00,   6.00,  None, None, None),                       # intro, walk-in
    (6.00,   11.90, "Wąsik, poznajesz mnie? To ja, kierownik.", None, None),
    (11.90,  17.90, "Zaklinam was, córy jerozolimskie, na gaze i łany polne…", None, None),
    (17.90,  23.90, "Nie budźcie ani nie rozbudzajcie ukochanej, póki nie zechce sama.", None, None),
    (23.90,  29.00, "Zechce, nie zechce, ale muszę.", None, None),
    (29.00,  33.10, "– Wstałem.\n– Wstawaj, Wąsik, KIA cię wzywa.", None, None),
    (33.10,  36.70, "– Ale po co? – Sportki się sprzedawały.", None, None),
    (36.70,  40.10, "Właśnie był zamach na plan sprzedaży.", None, None),
    (40.10,  41.90, "Udany?", None, None),
    (41.90,  44.10, "O, na szczęście nie.", None, None),
    (44.10,  46.90, "Ale musisz ratować sytuację.", None, None),
    (46.90,  50.20, "Sportage, Seltos i XCeed w specjalnych cenach", None, None),
    (50.20,  52.30, "A ty sobie Hawaję urządzasz.", None, None),
    (52.30,  54.70, None, None, None),
    (54.70,  57.90, "No to kierownik, jak to się stało?", P1, 0.0),
    (57.90,  61.70, "Klienci zobaczyli nowe ceny.", None, None),
    (61.70,  63.40, "I co?", None, None),
    (63.40,  65.50, "I zaczęli kupować.", None, None),
    (65.50,  67.30, "Ja już niedługo odchodzę na rentę,", None, None),
    (67.30,  69.90, "bo te zakupy mnie do grobów prowadzą.", None, None),
    (69.90,  72.60, "Pomyślałem, że mógłbyś zająć moje miejsce.", None, None),
    (72.60,  76.20, None, None, None),                       # reaction
    (76.20,  80.10, "Oczywiście, jak zaczniesz więcej sprzedawać.", None, None),
    (80.10,  83.00, "A naród ma zdolność kredytową?", None, None),
    (83.00,  85.30, "Wąsik, naród Cię potrzebuje.", None, None),
    (85.30,  87.90, None, None, None),
    (87.90,  91.90, "To niech przyjeżdża, tylko niech sprawdzi, czy ma wkład własny.", P2, 0.0),
    (91.90,  93.40, None, None, None),                       # whip pan to desk
    (93.40,  95.60, "Jeśli podobały Ci się żartobliwe filmiki,", P3, 0.0),
    (95.60,  98.00, "Zostaw reakcję, zostaw komentarz,", P3, 2.2),
    (98.00,  100.40, "A super Wąsik leci ratować sytuację.", P3, 4.6),
    (100.40, 102.70, None, None, None),                      # outro tail
    (102.70, 109.80, None, DRONE, None),                     # drone + teleadresowa
]

DRONE_START = 102.70

scenes = []
for start, end, caption, file, src_start in TIMELINE:
    text = caption
    if text and text.startswith("@"):
        raise SystemExit(f"placeholder caption not filled: {text}")
    if file:
        src = src_start if src_start is not None else 0.0
    else:
        src = start
    scene = {"file": file or MASTER,
             "start": round(src, 3),
             "duration": round(end - start, 3)}
    if caption:
        scene["title"] = {**CAPTION, "body": caption}
    scenes.append(scene)

manifest = {
    "name": "kia-nowicki-killer3-reel",
    "brand": "kia-nowicki",
    "video": {"width": 1080, "height": 1920, "fps": 30},
    "output": "renders/kia-nowicki/kia-nowicki-killer3-reel.mp4",
    "music": {
        "file": "imports/audio/killer3_dialog_padded.m4a",
        "start": 0.0,
        "volume": 1.0,
        "fade_out": 0.6
    },
    "voiceover": {
        "file": "imports/audio/nowicki-kalisz-radio-dogrywka-teleadresowa.wav",
        "start": 0.0,
        "offset_seconds": DRONE_START + 0.2,
        "volume": 0.6
    },
    "scenes": scenes,
}

path = "brands/kia-nowicki/projects/kia-nowicki-killer3-reel.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"wrote {path} with {len(scenes)} scenes, total {TIMELINE[-1][1]}s")
