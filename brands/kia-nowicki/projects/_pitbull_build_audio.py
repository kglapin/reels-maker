#!/usr/bin/env python3
"""Build the PITBULL dialog track: censor beeps for both swears + padding.

Swear windows (seconds in the graded master / final timeline):
- 16.00-16.36  swallowed swear in "Nie, się ^#%@$^ podszywają." (ASR missed it)
- 41.48-42.30  "Czy tam, kurwa, Neptun?" (punch-in 2)
Each window is silenced on the original dialog and covered with a 1 kHz tone
(same treatment as the killer3 scheme). Output: masked (59.28s) with original
dialogue elsewhere and a padded (67.3s) copy that covers the whole reel.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOOT = ROOT / "brands/kia-nowicki/imports/footage"
AUDIO = ROOT / "brands/kia-nowicki/imports/audio"
MASTER = FOOT / "pitbull_graded.mp4"
MASKED = AUDIO / "pitbull_dialog_masked.m4a"
PADDED = AUDIO / "pitbull_dialog_padded.m4a"

BEEPS = [(16.00, 16.36), (41.48, 42.30)]
TOTAL = 67.30


def run(cmd):
    subprocess.run(cmd, check=True, cwd=ROOT)


windows = "+".join(
    f"between(t,{a:.2f},{b:.2f})" for a, b in BEEPS)
silence = f"volume=enable='{windows}':volume=0"

# 1. silence the swear windows on the original dialog
run([
    "ffmpeg", "-v", "error", "-y", "-i", str(MASTER), "-vn",
    "-af", silence, "-c:a", "pcm_s16le", str(AUDIO / "_pitbull_clean.wav"),
])

# 2. build one beep per window and mix on top of the silenced dialog
inputs, filters, mix = [], [], []
for i, (a, b) in enumerate(BEEPS):
    d = b - a
    inputs += ["-f", "lavfi", "-t", f"{d:.3f}",
               "-i", "sine=frequency=1000:sample_rate=44100"]
    fade = 0.03
    filters.append(
        f"[{i + 1}:a]volume=0.9,afade=t=in:st=0:d={fade},"
        f"afade=t=out:st={d - fade:.3f}:d={fade},"
        f"adelay={int(round(a * 1000))}|{int(round(a * 1000))}[b{i}]")
    mix.append(f"[b{i}]")
filters.append(f"[0:a]{''.join(mix)}amix=inputs={len(BEEPS) + 1}:"
               "duration=first:normalize=0[a]")

run([
    "ffmpeg", "-v", "error", "-y", "-i", str(AUDIO / "_pitbull_clean.wav"),
    *inputs,
    "-filter_complex", ";".join(filters),
    "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(MASKED),
])

# 3. pad with silence so the music track covers the whole reel
run([
    "ffmpeg", "-v", "error", "-y", "-i", str(MASKED),
    "-af", f"apad=pad_dur={TOTAL - 59.28:.2f}", "-t", f"{TOTAL:.2f}",
    "-c:a", "aac", "-b:a", "192k", str(PADDED),
])
print(f"masked {MASKED.name} ({[f'{a:.2f}-{b:.2f}' for a, b in BEEPS]})")
print(f"padded {PADDED.name} to {TOTAL:.2f}s")
