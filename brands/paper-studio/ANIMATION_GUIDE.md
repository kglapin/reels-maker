# Paper Tear Animation Assets — reuse guide

This directory documents reusable paper‑tear reveal animations in the
`reels_maker` studio pipeline. Project manifests and code are tracked; the
third‑party source footage and keyed frames are local-only in the git-ignored
`imports/` quarantine, with provenance records kept beside them.

## Folder structure (under `brands/paper-studio/`)

```
imports/paper-tear/
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
| 1 – baza      | `imports/paper-tear/keyed`                  | 0.32         | 18                | 4.2 s    | centre → outward tear      |
| 2 – rolka     | `imports/paper-tear/variants/b/keyed`      | 0.32         | 17                | 3.0 s    | sheet rolled down from top |
| 3 – przekątna | `imports/paper-tear/variants/e/keyed`      | 0.55         | 35                | 3.5 s    | diagonal peel + curl       |
| 4 – szczelina | `imports/paper-tear/variants/f/keyed`      | 0.32         | 17                | 3.0 s    | V‑shaped slit from top     |
| 5 – narożnik  | `imports/paper-tear/variants/g/keyed`      | 0.32         | 11                | 2.3 s    | corner tear across height  |

All variants use the same copy layout (kicker / headline / subtitle) that is
**typeset from frame one** and revealed purely by the tear — no fade‑in.

## Re‑creating the keyed footage (if you ever need new material)

```sh
# One‑off: download + key a time window
python tools/prepare_paper_tear_footage.py \
  --brand paper-studio \
  --source-youtube EQNIm_LSbFo \
  --start 3.64 --duration 1.6 \
  --rights-note "Owner confirmed reuse for the paper‑tear demo on 2026‑10‑27."
# → writes keyed frames + provenance.json into imports/paper-tear/keyed/
```

The script respects the repository policy: all output stays under
`brands/*/imports/` (git‑ignored quarantine) and a `provenance.json` record is
written alongside.

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
`https://www.youtube.com/shorts/EQNIm_LSbFo`. The owner authorised reuse for
this demo on **2026‑10‑27** (recorded in every `provenance.json`). Before any
publication beyond the demo, replace this note with a verifiable licence or
stock‑footage ID and resolve the repository’s privacy gate.

---

**Need a new variant or a different tear window?**
Run the preparation script with different `--start` / `--duration` values, or
point it at a different source file. The resulting `keyed/` folder can be added
to `projects/<name>.json` under a new `tear_sequence` entry.
