# Paper-tear capture — rights and provenance record

**Status: approved for inclusion in this project by user confirmation.**

| Field | Value |
|---|---|
| Intended use | `brands/paper-studio/projects/paper-tear-captured.json` (`paper_reveal` scene) |
| Material | Torn-paper reveal shot, green-screen capture, 1080×1920, 25 fps |
| Source | `https://www.youtube.com/shorts/EQNIm_LSbFo` |
| Permission | On 2026-10-27, the user confirmed they have permission to use and redistribute the source and derived frames |
| Repository state | Repository visibility was verified as **PRIVATE** on 2026-10-27; user also confirmed permission for public redistribution |
| Tracked location | `brands/paper-studio/media/fx/paper-tear/` |
| Source storage | `source.webm` is tracked through Git LFS |
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
`media/fx/paper-tear/provenance.json`. Candidate assets generated later still
belong in ignored `imports/` until reviewed and promoted.

## Rights and review limits

The repository contains the user's confirmation, not a separate licence
document or licence ID. It records the asserted permission; it is not an
independent legal opinion and does not certify rights beyond those the user
holds. Re-run `studio-qa --strict`, render the final profile, watch the MP4
with sound on a phone and record human review in `docs/REVIEW_RUBRIC.md` before
delivery of a finished animation.

This file documents provenance; it is **not** a legal opinion and does not
certify that the clip is cleared for commercial use.
