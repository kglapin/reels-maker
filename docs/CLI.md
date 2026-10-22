# Reels Maker CLI and manifest contract

Install with `python -m pip install -e .` (Python >=3.11, FFmpeg/FFprobe).

```sh
reels-maker doctor --json
reels-maker catalog --brand asta-energy --json
reels-maker catalog --brand asta-energy --probe --limit 100 --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --syntax-only --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --jobs 2 --json
reels-maker inspect renders/asta-energy/asta-rush-demo.mp4 --json
```

Use `--root /absolute/repository` to run from elsewhere. All commands are
noninteractive. Successful responses go to stdout as one JSON object; errors
go to stderr with a nonzero exit code. Harnesses should inspect process return
codes before trusting the `output` path.

## Brand-scoped manifests

Place one `brand.json` and `BRAND.md` under `brands/<slug>/`.
Each project is an independent manifest under `brands/<slug>/projects/`:

```json
{
  "name": "short-reel",
  "brand": "asta-energy",
  "video": {"width": 1080, "height": 1920, "fps": 25},
  "scenes": [
    {"file": "media/footage/2_dron-pv-dla-firm-asta.mp4", "start": 0, "duration": 3,
     "framing": "crop", "title": {"headline": "Fotowoltaika dla firm"}}
  ],
  "output": "renders/asta-energy/short-reel.mp4"
}
```

`branding` (accent/logo) inherits from the brand manifest. Explicit per-project
overrides are supported. All `scenes[].file`, `music.file`, and logo paths
are relative to the selected brand root and are restricted to that brand.
Videos, audio and effects must be on local disk; Git LFS pointers are detected
and produce an actionable error.

## Rendering and performance

The media layer checks each unique input once with FFprobe. Encoder inputs are
normalized to the same frame format and size; segments are hashed by source
metadata and settings, cached, and assembled by stream-copy. FFmpeg only encodes
cache misses. Audio is encoded separately and multiplexed without re-encoding
video. Scene frame counts are computed from cumulative cut points.
Use `--jobs 1..8` based on available CPU and memory. `--no-cache` forces
rebuilds; `--cache-dir` selects another cache location.

Do not assume `brand.json` font-family guidance automatically installs or
embeds a font. Until explicit font-file selection is implemented and tested,
the renderer uses a locally installed compatible fallback.

## Brand-safe typography and performance timings

The renderer uses optional `branding.safe_areas` from the individual project to position its logo and text. The brand preset never imposes resolution, aspect ratio, frame rate or platform-specific margins. `branding.font_family` chooses an installed Open Sans family when available, otherwise DejaVu Sans (no bundled fonts). Explicit `font_regular`/`font_bold` file paths can override font discovery; font licensing is the operator's responsibility.

Each render reports `timings_seconds.preflight`, `scene_encoding`, `assembly_audio_validation`, and `total` plus `cache_hit_rate`. Compare a cold render to a repeated warm render before choosing a concurrency level. These are measurements, not promised speed-ups.
