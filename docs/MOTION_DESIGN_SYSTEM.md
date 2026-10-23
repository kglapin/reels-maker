# Native Motion-Design System

The studio renderer is a reusable, brand-aware composition layer alongside the
existing FFmpeg scene renderer. It does not fork the CLI, rewrite legacy
manifests, or make a computer-generated design automatically “approved.”

## Architecture

```text
studio manifest + brand.json + reviewed media
        ↓
StudioProject → DesignTokens / LayoutEngine → scene components
        ↓                                   ↓
frame-quantized Timeline              retained SceneGraph
        ↓                                   ↓
Pillow SceneRenderer ← choreography / keyframes / transitions
        ↓
FFmpeg H.264 + optional independent voice/music mux
        ↓
studio-qa + real-MP4 storyboard → human review
```

- `design/`: WCAG color utilities, scaled tokens and five `StyleSystem`s.
- `layout/`: constraint-based recipes with safe-area validation.
- `textkit/`: Pillow font metrics, Unicode-aware wrapping, fitted/rich text and
  number formatting.
- `motionkit/`: easing, tracks, entrances, camera drift and deterministic cue
  scheduling.
- `core/`: retained nodes, sampled properties, timeline quantization and QA
  geometry.
- `components/`: reusable icon primitives and scene builders. Legacy kinetic
  `type` names still dispatch through the existing mapping.
- `assets/`: media catalog, review-state/license metadata and deterministic
  video still extraction.
- `audiokit/`: phrase-to-timestamp cue mapping and restrained SFX proposals.
- `renderers/`: Pillow raster output and FFmpeg delivery pipeline.
- `qa/`: collisions, safe areas, typography overflow, rendered contrast,
  reading hold, declared values, asset review and motion variety.

Five reusable styles are registered in `design/styles.py`:
`editorial-premium`, `kinetic-advertising`, `product-cinematic`,
`data-storytelling` and `social-native`. Styles alter hierarchy, type scale,
spacing, safe margins, motion vocabulary and transition choices; they do not
select different renderer implementations.

### Negative/knockout word fill

Rich-text runs may opt into a pixel-negative glyph fill:

```json
"headline": {"runs": [
  {"text": "ENERGIA, KTÓRA", "scale": 0.9, "color": "white"},
  {"text": "ZOSTAJE", "scale": 1.18, "weight": "bold",
   "color": "white", "break_before": true, "effect": "negative"}
]}
```

Only the marked word's glyph mask inverts the already-composited scene pixels;
other words and the full-frame background remain untouched. It is intentionally
limited to a single word of at most 18 characters, bold weight, a run scale of
at least 1.08 and a rendered font size of at least 32 px. Use a heavy font and
reserve it for one short focal word over full-bleed imagery. The effect must be
a top-level text element so it can sample
the actual scene surface. Because arbitrary imagery can contain mid-tones,
strict QA emits a human-review warning instead of claiming automatic contrast
approval; inspect the actual MP4 at phone size.

## Manifest essentials

Projects remain under `brands/<slug>/projects/`; relative input paths are
resolved within that brand. A minimal example:

```json
{
  "name": "sample-reel",
  "brand": "asta-energy",
  "style": "editorial-premium",
  "video": {"width": 1080, "height": 1920, "fps": 30},
  "export": {"profile": "final", "crf": 17, "preset": "slow"},
  "scenes": [
    {"composition": "amount", "duration": 3.2,
     "kicker": "PRZYKŁADOWA DANA", "value": 16000,
     "format": {"suffix": " zł", "thousands": " "},
     "subtitle": "Dane poglądowe", "visual": "none"}
  ]
}
```

Scene components accept structured content such as `items`, `columns`,
`milestones`, `bars`, `stats`, `photo` and `background`. `cues` map semantic
element roles to scene-local seconds; `cue_frames` map roles to integer frame
offsets. Use only one representation. If `audio.transcript` is provided, JSON
must contain manually verified word-level records (`text`/`word`, `start`,
`end`). SRT/VTT cue boundaries can drive phrase-level hints but are reported as
caption-level, not exact word synchronization. Segment timestamps are rejected;
the engine never estimates individual speech onsets from a sentence or raw
audio.

Audio remains opt-in. Independent `music`/`voiceover` tracks support explicit
level, offsets, fade-out and optional sidechain ducking. `audio.sfx` is an
array of brand-relative files with a scene-timeline `time` and either linear
`volume` or `gain_db`; tracks are padded/trimmed to the quantized duration,
mixed to stereo AAC and peak-limited. The studio integration test uses
generated tones only; it does not verify a brand music licence or creative
mix quality.

## Profiles and commands

| Profile | Dimensions | FPS | Intended use |
|---|---:|---:|---|
| `preview` | 360×640 | 20 | Fast layout checks |
| `review` | 720×1280 | 30 | Motion/readability review |
| `final` | 1080×1920 | 30 | Reels publication master |
| `high-motion` | 1080×1920 | 60 | Selected motion-heavy work |

```sh
reels-maker studio-inspect brands/asta-energy/projects/example.json --profile review --json
reels-maker studio-qa brands/asta-energy/projects/example.json --profile review --strict --json
reels-maker studio-render brands/asta-energy/projects/example.json --profile final --supersample 1 --json
reels-maker storyboard brands/asta-energy/projects/example.json --video renders/asta-energy/example-final.mp4 --output renders/asta-energy/qa/example.png --motion-strip --json
```

`storyboard` verifies the encoded MP4's dimensions, FPS, exact frame count and
expected audio structure before sampling actual frames. For a non-default
render profile, pass the same `--profile` to the storyboard command.

## QA and human gates

Strict studio QA blocks on geometry collisions, safe-area escapes, text overflow
or truncation, low measured contrast, insufficient readable hold, invalid
declared data and unapproved finished promos. Unreviewed footage is a warning,
not assumed clean. The JSON report also states limits: border-ring contrast
sampling is approximate on complex imagery, aesthetic quality is not scored,
music ducking and pumping require listening, and brand/legal facts need an owner
check. Review the real MP4 and contact sheet at phone size before approval.

The included `asta-motion-system-demo.json` is an implementation sample, not a
claim-approved flagship. Its plotted numbers and process labels are marked as
illustrative. Rights for supplied music were not confirmed, so that demo is
silent. The reviewed stock clips used there are CC0 and recorded in
`brands/asta-energy/media/asset-reviews.json` and `licensing/stock_credits.txt`.
Final creative approval, brand-use approval and publication rights remain
human gates.

## Local acceptance evidence (2026-10-23)

- `146` repository tests passed (`unittest discover`).
- Final-profile studio QA passed for 13 scenes / 78 geometry samples plus 39
  rendered contrast-frame samples, with zero errors and one explicit warning
  to manually inspect the negative-filled word on actual footage.
- Real MP4: `renders/asta-energy/asta-motion-system-demo-final.mp4` — H.264,
  yuv420p, 1080×1920, 30 fps, 1,260 frames, 42.0 seconds; encoder metadata
  verified before atomic publication.
- Real-frame contact sheet:
  `renders/asta-energy/qa/asta-motion-system-demo-final.png`; motion strip:
  `renders/asta-energy/qa/asta-motion-system-demo-motion-strip.png`.
- Measured local render time: 91.24 seconds (13.81 rendered fps) at
  supersample 1. This is a single-machine measurement, not a before/after
  benchmark.
- The file is intentionally silent pending music-rights verification. Human
  phone playback, editorial scoring, and publication approval are still open.
