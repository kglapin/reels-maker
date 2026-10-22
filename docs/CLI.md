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

## Curated transitions (FFmpeg xfade)

All transitions are **opt-in**, and ordinary cuts are the default. To apply a
short, considered edit on a following shot:

```json
{"file":"media/footage/next.mp4","duration":2,
 "transition_in":{"type":"dissolve","frames":5}}
```

Types: `cut`, `dissolve`, `dip_to_black`, `motion_wipe_left`,
`motion_wipe_right`. An effect lasts at most 0.35 seconds and at most a third
of either adjacent shot, with a minimum of two frames. Movement wipes require
corresponding camera motion; avoid indiscriminate zooms, flashes, and presets.

The FFmpeg `xfade` transition **overlaps** N frames: final duration is the
frame-quantized scene sum *minus* all overlap frames. Therefore it alters cut
positions; avoid dissolves on beat-locked projects unless the soundtrack and
timing are re-planned. Projects with only cuts retain the cached segments and
fast stream-copy assembly. Any xfade incurs an assembly encode, but the cached
individual scenes remain reusable. The JSON render result reports `transitions`,
`transition_overlaps_frames` and `assembly_mode`.

## Editorial per-element motion (not a transition)

An optional `motion` object animates **individual elements of an existing title
card**: logo, accent, kicker, headline, body and footer. Each part is isolated
as its own transparent layer and introduced through a brief alpha fade with a
small ease-out movement. No random effects, bounce, typing, 3D rotation or
letter-by-letter animation.

```json
{"file":"media/footage/clip.mp4","duration":2.4,
 "title":{"kicker":"ASTA ENERGY","headline":"Energia dla firm",
          "body":"Projekt. Montaż. Serwis."},
 "motion":{"preset":"editorial_reveal","duration_frames":7,
           "stagger_frames":2,"distance_px":24}}
```

`fade_stagger` offers the same separate opacity ramps without movement and
requires no distance parameter. Timing is frame-based for consistent playback.
Safe ranges: reveal 2–0.45 s, stagger 0–0.15 s, distance 0–64 px at 1080px
reference width. The renderer refuses an entrance that cannot complete within
the scene. Motion is **off by default** and leaves existing static cards intact.
The media, branding and project files remain format-independent.

## Emphasized words and motion presets

The headline may be a plain string or a structured array of styled text runs:

```json
"title": {
  "kicker": "ASTA ENERGY",
  "headline": {
    "runs": [
      {"text": "Zwiększ ", "scale": 0.78, "color": "white"},
      {"text": "ZYSK", "scale": 1.35, "color": "accent",
       "weight": "bold"},
      {"text": " z energii", "scale": 0.78, "break_before": true}
    ]
  },
  "body": "Fotowoltaika i magazyny energii dla firm"
},
"motion": {"preset": "rise_soft", "duration_frames": 7,
           "stagger_frames": 2, "distance_px": 18}
```

The renderer measures actual glyph widths, wraps words and respects safe text
areas. A highlighted run may be 65–145% of the standard headline size.
Colors are restricted to `white`, `accent`, `muted`, so the brand palette
remains the single source of truth; no arbitrary HTML/CSS enters the manifest.

Deliberate entrance styles: `fade_stagger` (opacity only),
`editorial_reveal` and `rise_soft` (gentle upward movement),
`slide_left` and `slide_right` (horizontal movement). Motion always
stops; it is not applied by default. Use one style per scene and prefer short,
stable reading windows rather than continuous gimmicks.

## Format-independent safe areas and typography

`branding.safe_areas.horizontal_pixels`, `top_pixels` and `bottom_pixels`
are **literal pixels of the project's output dimensions**. They are not
interpreted as coordinates relative to a 1080×1920 reference frame and are
not stored in the brand preset. Missing values default to proportional margins
(8.5% horizontal/top; 13% bottom) for the project's own canvas; publishing
platform overlays should be checked before release.

Font and accent spacing use the shorter canvas side as their reference,
so a 1920×1080 composition does not grow titles to 177% of the portrait size.
Changing format still requires creative review of line breaks, text placement,
subject framing and UI overlays; automatic scaling is not a substitute.

## Technical export verification

The renderer verifies the **actual encoded H.264 MP4** before moving it into
the public output path: video codec `h264`, pixel format `yuv420p`,
resolution, average FPS, exact video frame count, video track duration, and
presence/absence of a single AAC audio track according to the project manifest.
If any check fails, the previous successfully exported MP4 is retained.

```sh
reels-maker verify brands/asta-energy/projects/example.json \
  --video renders/asta-energy/example.mp4 --json
```

This `verify` command can be run on an existing MP4 without encoding.
Export metadata is reported under `export_quality` after a render. These
checks protect technical delivery but do not judge artistic merit, colour
grading, speaker intelligibility or source licence compliance.
