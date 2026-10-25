# Reels Maker Operator Manual (REL-12)

> This manual covers both the legacy brand-scoped renderer and the opt-in
> Native Studio. Their JSON inputs differ; use the section matching the
> manifest you are rendering.

## Overview

Reels Maker is a local Python/FFmpeg toolchain for short-form video. The legacy
renderer consumes brand-scoped project manifests. The Native Studio uses
Creative Spec v1 and supports reusable compositions such as photo carousels and
the three-row photo marquee. Both require local source assets and a review of
the rendered output.

Requires Python 3.11 or later and FFmpeg/FFprobe. H.264 export requires an
FFmpeg build with the `libx264` encoder.

## Installation

```sh
git clone <repo-url>
cd reels-maker
python -m pip install -e .
```

Install optional dependencies only when needed: `python -m pip install -e '.[pdf]'`
for brandbook PDF output; see `pyproject.toml` for available extras.

## Quick Start

### Legacy brand-scoped project

```sh
reels-maker catalog --brand asta-energy --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --root . --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --root . --jobs 2 --json
reels-maker storyboard brands/asta-energy/projects/asta-rush-demo.json \
  --video renders/asta-energy/asta-rush-demo.mp4 \
  --output renders/asta-energy/qa/contact-sheet.png --json
```

### Native Studio / Creative Spec

```sh
reels-maker creative-validate examples/photo-marquee-demo.json --json
reels-maker creative-render examples/photo-marquee-demo.json \
  --output renders/photo-marquee-preview.mp4 \
  --storyboard renders/photo-marquee-storyboard.png --json
```

See [MOTION_DESIGN_SYSTEM.md](MOTION_DESIGN_SYSTEM.md) for supported Studio
compositions, profiles, manifest examples and QA limits.

## CLI Reference

```
reels-maker catalog --brand <brand> --json
reels-maker validate <legacy-manifest> --root . --strict-quality --json
reels-maker render <legacy-manifest> --root . --strict-quality --json
reels-maker storyboard <manifest> --video <mp4> --output <png> --json
reels-maker creative-validate <creative-spec.json> --json
reels-maker creative-compile <creative-spec.json> --output <studio.json> --json
reels-maker creative-render <creative-spec.json> --output <mp4> --storyboard <png> --json
reels-maker studio-inspect <studio-manifest> --profile review --json
reels-maker studio-qa <studio-manifest> --profile review --strict --json
reels-maker studio-render <studio-manifest> --profile final --json
```

## Legacy Project Manifest Fields

The table below describes legacy brand-scoped render manifests. It does not
describe Creative Spec v1; see [CLI.md](CLI.md) and
[MOTION_DESIGN_SYSTEM.md](MOTION_DESIGN_SYSTEM.md) for Studio inputs.

| Field | Required | Description |
|-------|----------|-------------|
| name | yes | Project name |
| video | yes | width, height, fps |
| scenes | yes | Array of scene objects |
| scenes[].file | yes | Footage path (relative to brand root) |
| scenes[].duration | yes | Scene duration in seconds |
| scenes[].title | no | Text overlay (kicker, headline, body, footer) |
| scenes[].motion | no | Animation preset and timing |
| scenes[].transition_in | no | Optional transition from previous scene |
| music | no | Music track settings |
| voiceover | no | Narrator track with sync_marks |
| branding | no | Logo/color overrides |
| output | yes | Output MP4 path |
| brand | no | Brand slug (for brand.json inheritance) |

## Known Limitations

1. **Narration alignment:** word timing in `voiceover.sync_marks` is supplied
   manually; the tool does not infer verified word onsets.
2. **Fonts:** rendering depends on locally available fonts; see the typography
   and icon documents for supported discovery and fallback behavior.
3. **Repository visibility:** this GitHub repository is public (verified
   2026-10-25). Treat committed files as public. Never add secrets or
   confidential client materials; use approved private storage for them.
4. **Automated review:** CI and QA check technical contracts but do not approve
   creative quality, asset rights, brand use or publication.
5. **No auto-publish:** exports are written locally; publishing is a separate
   human action.
6. **Performance:** the default render path uses CPU encoding. Check the
   selected FFmpeg build and profile for the actual export configuration.

## Troubleshooting

### "Asset not found"
- Verify the file path is relative to the brand directory
- Check if the Git LFS payload is hydrated: `git lfs pull`

### "source_is_prebranded" warning
- The selected footage has baked-in graphics (logo, captions)
- Replace with clean_source footage or disable logo overlay
- Check `media/asset-reviews.json` for classification

### "Invalid motion timing"
- Cue timestamps must target valid text roles
- Check role names: kicker, headline-0, headline-1, etc.
- Ensure cues leave at least 0.55s of settled reading time

### "sidechain requires two tracks"
- Music ducking requires both voiceover and music tracks
- Remove `music.ducking` or add a `voiceover` section

### Export quality check fails
- Verify codec is h264, pixel format yuv420p
- Check frame count matches expected duration × FPS
- Ensure AAC audio if music/voiceover present
