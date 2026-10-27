# Paper-tear capture — rights and provenance record

**Status: quarantine only. Do not publish.**

| Field | Value |
|---|---|
| Intended use | `brands/paper-studio/projects/paper-tear-captured.json` (`paper_reveal` scene) |
| Material | Torn-paper reveal shot, green-screen capture, 1080×1920, 25 fps |
| Source | `https://www.youtube.com/shorts/EQNIm_LSbFo` |
| Permission | Owner stated on 2026-10-27 that the material may be used for this demo |
| Repository state | Repository is **PUBLIC**; third-party footage is therefore kept out of git |
| Local location | `brands/paper-studio/imports/paper-tear/` (git-ignored quarantine) |
| Derivative | `keyed/f_0001.png` … `f_0040.png` — chroma-keyed RGBA frames |

## How the frames were produced

```sh
python tools/prepare_paper_tear_footage.py \
  --brand paper-studio \
  --source-youtube EQNIm_LSbFo \
  --start 3.64 --duration 1.6 \
  --rights-note "Owner confirmed reuse for the paper-tear demo on 2026-10-27."
```

The tool records the source SHA-256, key parameters and the rights statement in
`imports/paper-tear/provenance.json`.

## Before any publication

1. Replace the spoken/owner permission with a written licence reference that a
   reviewer can verify independently (platform licence, stock licence ID or
   signed release).
2. Move the reviewed asset into `brands/paper-studio/media/fx/` only after the
   repository privacy gate (SEC-06) is resolved.
3. Re-run `studio-qa --strict`, render the final profile, watch the MP4 with
   sound on a phone and record the human review in `docs/REVIEW_RUBRIC.md`.

This file documents provenance; it is **not** a legal opinion and does not
certify that the clip is cleared for commercial use.
