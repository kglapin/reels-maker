#!/usr/bin/env python3
"""Caption table for the PITBULL reel -> captions.json for the PIL builder.

Word times from Whisper large-v3-turbo; brand corrections: XCeed, "skrzynią".
Swear words replaced per BRAND.md with `^#%@$@^` ONLY (names and other words
unchanged). Captions from 10s sit higher (y=920-950), close to the vertical
centre but below faces; scene A (0-9s) stays at 1050.
The drift at 16s ("Nie, się ^#%@$@^ podszywają.") is a quiet swallowed swear
missed by ASR; audio beep covers 16.00-16.36 on the music track.
Drone outro captions are timed to the voiceover starting WITH the drone clip
(offset 59.267 = drone start).
"""
import json
from pathlib import Path

OUT = Path("renders/kia-nowicki/qa/captions_pitbull")
OUT.mkdir(parents=True, exist_ok=True)

MASTER = "pitbull_graded.mp4"
PUNCH1 = "pitbull_punch1_table.mp4"
PUNCH2 = "pitbull_punch2_neptun.mp4"
PUNCH3 = "pitbull_punch3_price.mp4"
DRONE = "drone_white_pitbull.mp4"


def W(text, t):
    return {"w": text, "t": t}


captions = [
    # ---- scene A: desk (before 10s, y stays where the owner approved it) ----
    {"target": MASTER, "local_t0": 0.0, "local_t1": 2.45, "y": 1050,
     "words": [W("Dobrze,", 0.00), W("panie", 0.54),
               W("Zbyszku,", 0.66), W("lepszej", 1.12), W("ceny", 1.50),
               W("nie", 1.74), W("znajdziemy.", 1.84)]},
    {"target": MASTER, "local_t0": 2.70, "local_t1": 3.45, "y": 1050,
     "words": [W("Piszemy?", 2.78)]},
    {"target": MASTER, "local_t0": 3.85, "local_t1": 5.40, "y": 1050,
     "words": [W("Muszę", 3.90), W("się", 4.38), W("jeszcze", 4.48),
               W("zastanowić.", 4.66)]},
    {"target": MASTER, "local_t0": 5.55, "local_t1": 6.35, "y": 1050,
     "words": [W("Ja", 5.64), W("dam", 5.76), W("znać.", 5.90)]},
    {"target": MASTER, "local_t0": 6.90, "local_t1": 8.15, "y": 1050,
     "words": [W("Dziękuję.", 6.96), W("Do", 7.60), W("zobaczenia.", 7.68)]},

    # ---- scene B: phone call (from 10s: higher, y=950) ----
    {"target": MASTER, "local_t0": 9.15, "local_t1": 9.80, "y": 950,
     "words": [W("Wąsik?", 9.22)]},
    {"target": MASTER, "local_t0": 9.90, "local_t1": 11.70, "y": 950,
     "words": [W("Słuchaj,", 9.96), W("jest", 10.50), W("u", 10.62),
               W("nas", 10.76), W("jakiś", 10.84), W("Zbigniew,", 11.12)]},
    {"target": MASTER, "local_t0": 11.78, "local_t1": 13.52, "y": 950,
     "words": [W("który", 11.82), W("mówi,", 12.02), W("że", 12.34),
               W("jakiś", 12.40), W("Wąsik", 12.64), W("z", 13.04),
               W("Kalisza", 13.16)]},
    {"target": MASTER, "local_t0": 13.52, "local_t1": 15.15, "y": 950,
     "words": [W("dał", 13.48), W("mu", 13.72), W("ekstra", 13.82),
               W("rabat", 14.20), W("na", 14.50), W("XCeed.", 14.66)]},
    # swallowed swear between "się" and "podszywają" (16.00-16.36) - beeped
    {"target": MASTER, "local_t0": 15.20, "local_t1": 17.05, "y": 950,
     "words": [W("Nie,", 15.36), W("się", 15.80), W("^#%@$@^", 16.02),
               W("podszywają.", 16.36)]},
    {"target": MASTER, "local_t0": 17.05, "local_t1": 17.90, "y": 950,
     "words": [W("Nic", 17.12), W("nie", 17.34), W("dawać.", 17.46)]},

    # ---- punch-in 1: Zbyszek realises Zbyszek == Zbigniew ----
    {"target": PUNCH1, "local_t0": 0.0, "local_t1": 2.30, "y": 950,
     "words": [W("A", 0.00), W("Zbyszek", 0.48), W("i", 0.96),
               W("Zbigniew", 1.14), W("to", 1.56), W("to", 1.66),
               W("samo", 1.78), W("imię?", 1.96)]},

    # ---- scene C: back at the table ----
    {"target": MASTER, "local_t0": 21.50, "local_t1": 23.15, "y": 940,
     "words": [W("Bo", 21.58), W("wczoraj", 22.06), W("był", 22.48),
               W("u", 22.68), W("mnie", 22.84)]},
    {"target": MASTER, "local_t0": 23.85, "local_t1": 25.85, "y": 940,
     "words": [W("Zbyszek,", 23.92), W("a", 24.58), W("teraz", 24.90),
               W("Zbigniew", 25.08), W("jest?", 25.50)]},
    {"target": MASTER, "local_t0": 26.55, "local_t1": 27.30, "y": 940,
     "words": [W("To", 26.64), W("samo.", 26.86)]},

    # ---- scene D: back turned under the logo ----
    {"target": MASTER, "local_t0": 29.15, "local_t1": 30.80, "y": 930,
     "words": [W("Tomek,", 29.24), W("porąbało", 30.00), W("mi", 30.42),
               W("się.", 30.52)]},
    {"target": MASTER, "local_t0": 31.05, "local_t1": 32.55, "y": 930,
     "words": [W("To", 31.12), W("jednak", 31.66), W("był", 31.80),
               W("ten", 31.94), W("Zbigniew.", 32.04)]},

    # ---- scene E: chasing the impostor ----
    {"target": MASTER, "local_t0": 33.40, "local_t1": 34.95, "y": 920,
     "words": [W("Ale", 33.46), W("on", 34.10), W("już", 34.26),
               W("wyszedł.", 34.40)]},
    {"target": MASTER, "local_t0": 35.10, "local_t1": 36.65, "y": 920,
     "words": [W("To", 35.18), W("go", 35.42), W("goń", 35.52),
               W("i", 35.80), W("powiedz", 36.28)]},
    {"target": MASTER, "local_t0": 36.50, "local_t1": 37.95, "y": 920,
     "words": [W("że", 36.58), W("nieporozumienie", 37.12), W("takie.", 37.58)]},
    {"target": MASTER, "local_t0": 38.30, "local_t1": 40.85, "y": 920,
     "words": [W("Nie", 38.38), W("każdy", 38.88), W("facet", 39.10),
               W("z", 39.38), W("widłami", 39.46), W("to", 39.72),
               W("Zeus.", 40.40)]},

    # ---- punch-in 2: the Neptune line (swear beeped + marker) ----
    {"target": PUNCH2, "local_t0": 0.0, "local_t1": 2.30, "y": 950,
     "words": [W("Czy", 0.04), W("tam,", 0.44), W("^#%@$@^", 0.74),
               W("Neptun?", 1.38)]},

    # ---- scene F: showroom, XCeed pitch ----
    {"target": MASTER, "local_t0": 43.50, "local_t1": 45.80, "y": 920,
     "words": [W("Pozostało", 43.60), W("nam", 44.24), W("kilka", 44.46),
               W("ostatnich", 44.98), W("sztuk.", 45.40)]},

    # ---- punch-in 3: the price (y=1150 clears the 109 900 price tag) ----
    {"target": PUNCH3, "local_t0": 0.0, "local_t1": 2.50, "y": 1150,
     "words": [W("109", 0.12), W("900", 0.60), W("za", 0.98),
               W("model", 1.20), W("Kia", 1.50), W("XCeed.", 2.10)]},

    # ---- scene F tail: specs + closing ----
    {"target": MASTER, "local_t0": 48.80, "local_t1": 50.35, "y": 920,
     "words": [W("W", 48.86), W("silnikiem", 49.34), W("1.6,", 49.72)]},
    {"target": MASTER, "local_t0": 50.50, "local_t1": 51.55, "y": 920,
     "words": [W("150", 50.56), W("koni,", 50.98)]},
    {"target": MASTER, "local_t0": 51.60, "local_t1": 54.00, "y": 920,
     "words": [W("z", 51.66), W("7-biegową", 51.98), W("skrzynią", 52.46),
               W("automatyczną.", 53.22)]},
    {"target": MASTER, "local_t0": 54.30, "local_t1": 56.05, "y": 920,
     "words": [W("Zbyszek,", 54.54), W("Zbigniew,", 55.16), W("czy", 55.74),
               W("ty...", 55.84)]},
    {"target": MASTER, "local_t0": 56.10, "local_t1": 57.30, "y": 920,
     "words": [W("każdy", 56.46), W("zgarnie", 56.76), W("to", 57.12)]},
    {"target": MASTER, "local_t0": 57.25, "local_t1": 58.70, "y": 920,
     "words": [W("w", 57.30), W("tej", 57.62), W("samej", 57.72),
               W("specjalnej", 58.00), W("cenie.", 58.38)]},
    # the two faint "Zbigniew." echoes (58.64, 59.06) play over the white dip,
    # no captions on the dip (killer3 precedent)

    # ---- drone outro: teleadresowa, timed to the voiceover starting WITH
    # the drone clip (wav starts at 59.267; local time = wav time) ----
    {"target": DRONE, "local_t0": 0.0, "local_t1": 1.24,
     "y": 1050,
     "words": [W("Nowicki", 0.00), W("zaprasza.", 0.44)]},
    {"target": DRONE, "local_t0": 1.24, "local_t1": 4.20,
     "y": 1050,
     "words": [W("Kalisz,", 1.22), W("ulica\n", 1.76),
               W("Stanczukowskiego", 2.10), W("18.", 2.84)]},
]

(OUT / "captions.json").write_text(
    json.dumps(captions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8")
print(f"wrote {OUT / 'captions.json'} with {len(captions)} captions")