# Reels Maker Operator Manual (REL-12)

## Overview
Reels Maker is a deterministic Python/FFmpeg CLI for producing professional
motion-design video reels from licensed footage, brand assets, and optional
narrator/music tracks. It runs locally on any workstation with Python 3.13+
and FFmpeg 8.x.

## Installation
```sh
git clone <repo-url>
cd reels-maker
pip install -e '.[pdf]'  # includes ReportLab for brandbook PDF
```

## Quick Start
```sh
# 1. Verify your brand is configured
reels-maker catalog --brand asta-energy --json

# 2. Validate a project manifest
reels-maker validate brands/asta-energy/projects/asta-flagship-01-editorial.json --root . --strict-quality --json

# 3. Render
reels-maker render brands/asta-energy/projects/asta-flagship-01-editorial.json --root . --strict-quality --json

# 4. Generate quality review materials
reels-maker storyboard brands/asta-energy/projects/asta-flagship-01-editorial.json \
  --video renders/asta-energy/flagship-editorial-benefit.mp4 \
  --output renders/asta-energy/qa/contact-sheet.png --json

reels-maker storyboard ... --motion-strip --output renders/asta-energy/qa/motion-strip.png --json

# 5. Review and archive
# Score against docs/REVIEW_RUBRIC.md (9 dimensions, 0-4 scale)
```

## CLI Reference
```
reels-maker catalog  --brand <name> --json     List branded media assets
reels-maker validate <manifest> --root . --strict-quality --json
reels-maker render   <manifest> --root . --strict-quality --json
reels-maker storyboard <manifest> --video <mp4> --output <png> --json
reels-maker cue-sheet <manifest> --json
reels-maker brandbook --brand <name> --json
```

## Project Manifest Fields
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
1. **Forced alignment**: Narration word timing must be manually provided in
   `voiceover.sync_marks`. Automatic transcription is NOT available.
2. **Font availability**: Open Sans is preferred; DejaVu Sans is the fallback.
   Fonts must be installed locally before rendering.
3. **Private repo**: All source and media are private. No public distribution.
4. **CI runner**: Private GitHub Actions runners are currently blocked by
   account billing quota (OPS-11). Run tests locally with `pytest`.
5. **No GPU acceleration**: Renders use CPU-only x264 encoding.
6. **No auto-publish**: Exports go to local disk only.

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
