# Paper Tear Animation Assets — reuse guide

This directory documents reusable paper‑tear reveal animations in the
`reels_maker` studio pipeline. The user confirmed permission to redistribute
the source and derived frames; the approved FX asset is tracked with the
project, and the original source video uses Git LFS.

## Folder structure (under `brands/paper-studio/`)

```
media/fx/paper-tear/
  source.webm            ← raw YouTube Short (EQNIm_LSbFo)
  provenance.json        ← source hash, key params, rights note
  keyed/
    f_0001.png … f_0040.png   RGBA frames, chroma‑keyed green out
  variants/
    b/keyed/ …           24 frames – rolled‑from‑top tear
    e/keyed/ …           48 frames – diagonal peel with flap
    f/keyed/ …           27 frames – V‑slit from top edge
    g/keyed/ …           22 frames – corner tear across sheet

projects/
  paper-tear-captured.json    ← baseline: centre‑out tear (4.2 s)
  paper-tear-variants.json    ← 5 variants in one MP (16 s)
```

## How to render

```sh
# 1️⃣ Baseline (centre‑out tear)
.venv/bin/reels-maker studio-render brands/paper-studio/projects/paper-tear-captured.json \
  --profile review --supersample 1 --no-cache \
  --output renders/paper-studio/paper-tear-captured.mp4 --json

# 2️⃣ Full comparison reel (all five scenes)
.venv/bin/reels-maker studio-render brands/paper-studio/projects/paper-tear-variants.json \
  --profile review --supersample 1 --no-cache \
  --output renders/paper-studio/paper-tear-variants.mp4 --json
```

For a single variant, copy its scene object from `paper-tear-variants.json`
into a one-scene project manifest, keeping the corresponding
`tear_sequence`, `tear_speed`, `tear_hold_frame`, and duration values.

## Variant quick‑reference

| ID | `tear_sequence`                              | `tear_speed` | `tear_hold_frame` | Duration | Description                |
|----|----------------------------------------------|--------------|-------------------|----------|----------------------------|
| 1 – baza      | `media/fx/paper-tear/keyed`                  | 0.32         | 18                | 4.2 s    | centre → outward tear      |
| 2 – rolka     | `media/fx/paper-tear/variants/b/keyed`      | 0.32         | 17                | 3.0 s    | sheet rolled down from top |
| 3 – przekątna | `media/fx/paper-tear/variants/e/keyed`      | 0.55         | 35                | 3.5 s    | diagonal peel + curl       |
| 4 – szczelina | `media/fx/paper-tear/variants/f/keyed`      | 0.32         | 17                | 3.0 s    | V‑shaped slit from top     |
| 5 – narożnik  | `media/fx/paper-tear/variants/g/keyed`      | 0.32         | 11                | 2.3 s    | corner tear across height  |

All variants use the same copy layout (kicker / headline / subtitle) that is
**typeset from frame one** and revealed purely by the tear — no fade‑in.

## Re‑creating the keyed footage (if you ever need new material)

```sh
# One‑off: download + key a time window
python tools/prepare_paper_tear_footage.py \
  --brand paper-studio \
  --source-youtube EQNIm_LSbFo \
  --start 3.64 --duration 1.6 \
  --rights-note "User confirmed use and redistribution permission on 2026‑10‑27."
# → writes keyed frames + provenance.json into imports/paper-tear/keyed/
```

The script writes candidate material under `brands/*/imports/` first
(git‑ignored quarantine) and places its provenance record there. Once approved,
promote the source and keyed frames into `media/fx/`, update the record paths,
and point the manifest at the tracked sequence; do not render production
projects from quarantine.

## QA & human gates

- `studio-qa --strict` passes with **0 errors** for both the baseline and the
  five-scene comparison reel (one `composition_monotony` warning is expected
  for these demo compositions).
- The motion‑strip PNGs are in `renders/<brand>/qa/`.
- Always review the real MP4 with audio on a phone before sign‑off (the clips
  are silent because the source YouTube Short had no audio; add a sound effect
  or voiceover later if needed).

## Code changes (what made this possible)

- **`src/reels_maker/components/paper_reveal.py`** – new composition that
  composites an approved RGBA frame sequence over authored copy; copy is
  typeset from frame one (no entrance fade).
- **`src/reels_maker/renderers/scene.py`** – `_sequence` node kind that picks a
  frame by playback time, with `hold_frame` support and a shared helper
  `sequence_frame_path()` used by both renderer and QA.
- **`src/reels_maker/qa/contrast.py`** – `_ring_coverage()` reads the exact
  alpha of the sequence frame above an element and skips contrast scoring when
  the overlay hides the copy, avoiding false “low contrast” errors.
- **`tests/test_paper_reveal.py`** – unit tests for frame advancement, hold
  behaviour, directory‑scope safety, and the new contrast‑occlusion logic.
- **`tools/prepare_paper_tear_footage.py`** – reproducible CLI to download,
  key, and document a new paper‑tear clip.

## License / rights note

All footage originates from the YouTube Short
`https://www.youtube.com/shorts/EQNIm_LSbFo`. On **2026‑10‑27** the user
confirmed they have permission to use and redistribute the source and derived
frames. This confirmation and source hash are recorded in each
`provenance.json`; no separate licence document or licence ID was supplied.
The confirmation is not an independent legal review and does not grant any
rights beyond those the user holds.

---

**Need a new variant or a different tear window?**
Run the preparation script with different `--start` / `--duration` values, or
point it at a different source file. The resulting `keyed/` folder can be added
to `projects/<name>.json` under a new `tear_sequence` entry.
