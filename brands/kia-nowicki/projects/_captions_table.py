#!/usr/bin/env python3
"""Caption table for the KILLER3 reel v2 -> captions.json for the ASS builder.

Text reconciled from Whisper medium + large-v3 word timings, with brand-name
corrections (Wąsik, KIA, jerozolimskie, wkład własny). Word times are seconds
in the TARGET FILE's local timeline. Lines marked in RECHECK need an ear
review before publishing.
"""
import json
from pathlib import Path

OUT = Path("renders/kia-nowicki/qa/captions")
OUT.mkdir(parents=True, exist_ok=True)

MASTER = "killer3_graded.mp4"

def W(text, t):
    return {"w": text, "t": t}

captions = [
    # ---- intro: meme label over the manager walking in (punch-in on door) ----
    {"target": "killer3_intro_punch.mp4", "local_t0": 0.4, "local_t1": 4.2,
     "y": 1270, "words": [W("*wchodzi kierownik*", 0.4)],
     "countdown": [
         {"n": "3", "t0": 0.3, "t1": 1.6},
         {"n": "2", "t0": 1.6, "t1": 2.9},
         {"n": "1", "t0": 2.9, "t1": 4.2},
     ]},

    # ---- sketch dialogue (wide shots; y=1120 stays below both faces) ----
    {"target": MASTER, "local_t0": 5.4, "local_t1": 11.0, "y": 1120,
     "words": [W("Wąsik,", 5.76), W("poznajesz", 6.72), W("mnie?", 7.30),
               W("To", 8.52), W("ja,", 9.00), W("kierownik.", 9.36)]},

    {"target": MASTER, "local_t0": 11.1, "local_t1": 17.2, "y": 1120,  # text per original sketch "Wstawaj Ryba"
     "words": [W("Zaklinam", 11.24), W("was,", 12.20), W("córy", 12.44),
               W("Jerozolimskie,", 12.90), W("na", 14.14), W("gazele,", 14.62),
               W("na", 15.46), W("łanie.", 15.88)]},

    {"target": MASTER, "local_t0": 17.3, "local_t1": 22.9, "y": 1120,  # text per original sketch
     "words": [W("Nie", 17.44), W("budźcie", 17.92), W("ze", 18.15),
               W("snu,", 18.40), W("nie", 19.10), W("rozbudzajcie", 19.58),
               W("ukochanej,", 20.30), W("póki", 21.62), W("nie", 22.10),
               W("zechce", 22.26), W("sama.", 22.66)]},

    {"target": MASTER, "local_t0": 23.2, "local_t1": 28.9, "y": 1120,  # text per original sketch
     "words": [W("Zechce,", 23.44), W("czy", 24.32), W("nie", 24.40),
               W("zechce,", 24.50), W("ale", 25.02), W("muszę.", 26.20)]},

    {"target": MASTER, "local_t0": 29.0, "local_t1": 33.0, "y": 1120,  # RECHECK: "KIA" vs "Kija"
     "words": [W("Wstawaj,", 29.36), W("Wąsik,", 30.16), W("KIA", 30.70),
               W("cię", 31.12), W("wzywa.", 31.34)]},

    {"target": MASTER, "local_t0": 32.9, "local_t1": 36.5, "y": 1120,  # RECHECK: "Sportki"
     "words": [W("–", 32.72), W("Ale", 32.80), W("po", 33.12), W("co?", 33.34),
               W("–", 33.60), W("Sportki", 33.84), W("się", 34.50),
               W("sprzedają.", 34.66)]},

    {"target": MASTER, "local_t0": 36.6, "local_t1": 40.3, "y": 1120,
     "words": [W("Właśnie", 36.60), W("był", 37.00), W("zamach", 37.20),
               W("na", 37.64), W("plan", 37.72), W("sprzedaży.", 37.94)]},

    {"target": MASTER, "local_t0": 39.5, "local_t1": 41.5, "y": 1120,
     "words": [W("Udany?", 39.60)]},

    {"target": MASTER, "local_t0": 41.6, "local_t1": 46.3, "y": 1120,
     "words": [W("O,", 41.66), W("na", 42.26), W("szczęście", 43.02),
               W("nie,", 43.54), W("ale", 43.82), W("musisz", 44.26),
               W("ratować", 44.66), W("sytuację.", 45.06)]},

    {"target": MASTER, "local_t0": 46.3, "local_t1": 50.1, "y": 1120,  # RECHECK: model names
     "photos": [
         {"path": "imports/photos/sportage.png", "t_in": 46.42, "t_out": 50.10},
         {"path": "imports/photos/seltos.png",   "t_in": 47.22, "t_out": 50.25},
         {"path": "imports/photos/xceed.png",    "t_in": 47.90, "t_out": 50.40},
     ],
     "words": [W("Sportage,", 46.42), W("Seltos,", 47.22), W("i", 47.70),
               W("XCeed", 47.90), W("w", 48.28), W("specjalnych", 49.16),
               W("cenach,", 49.82)]},

    {"target": MASTER, "local_t0": 50.2, "local_t1": 53.8, "y": 1120,
     "words": [W("a", 50.22), W("ty", 50.36), W("tutaj", 50.46),
               W("sobie", 50.68), W("Hawaje", 50.86), W("urządzasz.", 51.24)]},

    # ---- punch-in 1: Wąsik on the couch (y=1330 stays below the face) ----
    {"target": "punch1_couch.mp4", "local_t0": 0.05, "local_t1": 3.2,
     "y": 1330,
     "words": [W("No", 0.05), W("to", 0.15), W("kierownik,", 0.25),
               W("no", 0.80), W("i", 0.85), W("jak", 0.90), W("to", 1.15),
               W("się", 1.95), W("stało?", 2.10)]},

    {"target": MASTER, "local_t0": 58.5, "local_t1": 60.9, "y": 1120,
     "words": [W("Klienci", 58.62), W("zobaczyli", 59.38), W("nowe", 59.98),
               W("ceny.", 60.24)]},

    {"target": MASTER, "local_t0": 60.9, "local_t1": 62.8, "y": 1120,
     "words": [W("I", 60.98), W("co?", 61.74)]},

    {"target": MASTER, "local_t0": 62.8, "local_t1": 64.8, "y": 1120,
     "words": [W("I", 62.88), W("zaczęli", 63.64), W("kupować.", 64.04)]},

    {"target": MASTER, "local_t0": 64.8, "local_t1": 67.0, "y": 1120,
     "words": [W("Ja", 64.82), W("już", 65.58), W("niedługo", 65.74),
               W("odchodzę", 66.14), W("na", 66.56), W("rentę,", 66.66)]},

    {"target": MASTER, "local_t0": 67.0, "local_t1": 69.7, "y": 1120,  # RECHECK: "odkupy" per owner
     "words": [W("bo", 67.10), W("te", 67.38), W("odkupy", 67.50),
               W("mnie", 67.90), W("do", 68.02), W("grobu", 68.14),
               W("wprowadzają.", 68.44)]},

    {"target": MASTER, "local_t0": 69.7, "local_t1": 72.6, "y": 1120,
     "words": [W("Pomyślałem,", 69.76), W("że", 70.52), W("mógłbyś", 70.82),
               W("zająć", 71.22), W("moje", 71.56), W("miejsce.", 71.74)]},

    {"target": MASTER, "local_t0": 76.0, "local_t1": 79.5, "y": 1120,
     "words": [W("Oczywiście,", 76.04), W("jak", 76.56), W("zaczniesz", 77.12),
               W("więcej", 77.56), W("sprzedawać.", 77.78)]},

    {"target": MASTER, "local_t0": 79.5, "local_t1": 82.7, "y": 1120,
     "words": [W("A", 79.52), W("naród", 80.28), W("ma", 80.60),
               W("zdolność", 80.78), W("kredytową?", 81.20)]},

    {"target": MASTER, "local_t0": 82.7, "local_t1": 85.5, "y": 1120,
     "words": [W("Wąsik,", 82.74), W("naród", 83.60), W("Cię", 84.10),
               W("potrzebuje.", 84.22)]},

    # ---- punch-in 2: Wąsik on the couch ----
    {"target": "punch2_couch.mp4", "local_t0": 0.05, "local_t1": 4.0,
     "y": 1330,  # RECHECK: "wkład własny"
     "words": [W("To", 0.05), W("niech", 0.75), W("przyjeżdża,", 0.95),
               W("tylko", 1.45), W("niech", 2.10), W("sprawdzi,", 2.30),
               W("czy", 2.65), W("ma", 2.75), W("na", 2.82),
               W("wkład", 2.92), W("własny.", 3.20)]},

    # ---- punch-in 3: Wąsik at the desk, CTA (y=1180) ----
    {"target": "punch3_desk.mp4", "local_t0": 0.05, "local_t1": 1.6,
     "y": 1180,
     "words": [W("Jeśli", 0.05), W("podobały", 0.10), W("Ci", 0.40),
               W("się", 0.50), W("nasze", 0.60), W("żartobliwe", 0.90),
               W("filmiki,", 1.40)]},
    {"target": "punch3_desk.mp4", "local_t0": 1.9, "local_t1": 4.1,
     "y": 1180,
     "words": [W("zostaw", 1.91), W("reakcję,", 2.26), W("zostaw", 2.76),
               W("komentarz,", 3.60)]},
    {"target": "punch3_desk.mp4", "local_t0": 4.15, "local_t1": 6.5,
     "y": 1180,
     "words": [W("a", 4.16), W("Super", 4.46), W("Wąsik", 4.88),
               W("leci", 5.36), W("ratować", 5.94), W("sytuację.", 6.30)]},

    # ---- drone outro: teleadresowa (no faces; near centre) ----
    {"target": "drone_white.mp4", "local_t0": 0.6, "local_t1": 1.75,
     "y": 1050,
     "words": [W("Nowicki", 0.60), W("zaprasza.", 1.04)]},
    {"target": "drone_white.mp4", "local_t0": 1.75, "local_t1": 5.2,
     "y": 1050,
     "words": [W("Kalisz,", 1.82), W("ulica\n", 2.36),
               W("Stanczukowskiego", 2.70), W("18.", 3.44)]},
]

(OUT / "captions.json").write_text(
    json.dumps(captions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
print(f"wrote {OUT / 'captions.json'} with {len(captions)} captions")
