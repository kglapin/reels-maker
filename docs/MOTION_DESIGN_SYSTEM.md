# Native Motion-Design System

The studio renderer is a reusable, brand-aware composition layer alongside the
existing FFmpeg scene renderer. It does not fork the CLI, rewrite legacy
manifests, or make a computer-generated design automatically “approved.”

Legacy kinetic manifests can opt into the shared scene graph through
`kinetic-render --engine studio`. The adapter maps their scene types, accent,
audio paths and output path, but intentionally uses the new compositions and
choreography; exact Cairo-frame parity is not promised. The original Cairo
backend remains the default until the classic video `render` path and visual
parity are migrated and accepted.

Classic moving-footage projects can opt into studio-generated title overlays
with `render --title-engine studio`. The scene graph renders transparent RGBA
entrances while the existing FFmpeg pipeline continues to trim and composite
the original video. Legacy Pillow title cards remain the default until parity,
logo placement, backdrop and audio behavior are validated.

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

### Gravity word sequence with camera follow

The `gravity_words` Studio scene measures a long line of copy and animates each
word independently. Every word falls from rest under constant downward
acceleration, then rebounds from the floor with a configurable coefficient of
restitution. Each rebound loses energy, so the word makes several progressively
smaller ballistic hops before resting. As the next word enters, a smooth
rightward camera pan centers it while the earlier words move left.
The baseline remains implicit: the scene draws no floor rule. Trailing words
continue to move after crossing the physical frame edge; the viewport clips
only the portion beyond it, so each word disappears in parts instead of
vanishing as a whole. QA permits this explicitly tagged horizontal travel.

```json
{
  "type": "gravity_words",
  "duration": 11.1,
  "headline": "Lorem ipsum dolor sit amet, consectetur adipiscing elit",
  "word_drop": {
    "start": 0.24,
    "stagger": 0.5,
    "duration": 1.1,
    "distance_units": 168,
    "restitution": 0.48,
    "pan_duration": 0.11
  }
}
```

`start`, `stagger`, `duration` and `pan_duration` are seconds. `duration` is
the target time from release through the diminishing rebounds;
`pan_duration` controls the short camera move that ends as the next word
appears. `stagger` sets the spoken-word cadence and may be shorter than the
rebound settle time, so several words can be bouncing at once. `distance_units`
scales with the canvas short side (1080 reference units), and `restitution`
must be between 0.30 and 0.68.
Long copy can contain many words, provided each individual word fits the safe
content width. The camera centers each new word; older words remain visible as
they pass beyond the frame, where the viewport clips them progressively.
Leave a readable hold after the final landing.
For phone review, inspect multiple impact frames and the final hold in the
actual MP4.

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

## Search and prompt field

Any Studio scene may add a measured search or prompt capsule with
`search_field`. The capsule settles first, its magnifier enters next, then the
query types in at a steady character rhythm. The caret follows measured glyph
widths and blinks during the remaining hold. Leave scene boundaries as hard
cuts by default; smoothness comes from the staged motion inside each scene.
Use an explicit `transition_in` only when the story needs an overlay wipe or
dip, and set its easing to `smooth`, `out-cubic`, `in-out-cubic` or `linear`.
Studio transition-out effects use a smoothstep travel curve.

```json
{
  "type": "statement",
  "headline": "Znajdź właściwe rozwiązanie",
  "search_field": {
    "query": "magazyny energii dla firm",
    "placeholder": "Szukaj",
    "typing_start": 0.38,
    "typing_duration": 0.9,
    "width_ratio": 0.84,
    "center_y": 0.78
  }
}
```

`width_ratio` is relative to the scene's safe width; `center_x` and `center_y`
are normalized canvas positions. `height_units` uses the shared design scale.
The field rejects placements that leave the safe area and queries that do not
fit on one line. Colors can be set with `fill`, `text_color`, `muted_color`,
`border_color` and `cursor_color`.

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
check. When an opaque `sequence` overlay (for example a captured paper tear) is
drawn above an element, contrast is not scored against that overlay's pixels;
the check reads the overlay frame alpha and only judges frames where the copy is
actually visible. Review the real MP4 and contact sheet at phone size before approval.

For standard 9:16 vertical Reels, authored copy and illustrations stay inside
the shared content zone (7.5% side, 9% top and 16% bottom margins). Full-bleed
backgrounds and positions reached only during animation are exempt.

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
- Shared-engine migration smoke: a reviewed CC0 moving clip was rendered with
  both legacy title cards and studio title overlays including the actual ASTA
  logo and a strong contextual backdrop. Both MP4s passed export metadata
  verification, and the actual-frame contact sheets were inspected:
  `renders/asta-energy/qa/studio-title-overlay-parity-legacy.png` and
  `renders/asta-energy/qa/studio-title-overlay-parity-studio.png`. The visual
  treatments differ; studio mode remains opt-in pending owner review.
- The file is intentionally silent pending music-rights verification. Human
  phone playback, editorial scoring, and publication approval are still open.


## Animated photo-card carousel

Use the Studio `photo-carousel` composition when the sequence should keep several photographs visible as one continuous, looping unit. The active photo fills a larger center card; neighboring cards sit with wide gaps at roughly 42% scale, with a light image blur and lower opacity. Card frames keep an even photo inset on all four sides; that inset and the border stroke become thinner as a card recedes. Captions are omitted. Each off-center photo gets a visible but restrained, reproducible offset and tilt that eases away as it reaches center.

Creative Spec v1 accepts 3–12 local stills in `shots[].assets`. Set `layout` (or `composition`) to `photo-carousel`; `carousel.advance_seconds` controls how often the next photo takes the center, from 0.8 to 4 seconds. Set `carousel.direction` to `vertical` to move cards upward from the bottom into the center and out at the top; `horizontal` remains the default. The vertical composition omits headings, captions, and body text so the cards fill the scene. The center card grows sharply while the cards above and below stay smaller and softly blurred. Assets stay inside the project or brand asset scope.

```json
{
  "id": "portfolio",
  "headline": "Selected work",
  "layout": "photo-carousel",
  "assets": ["images/one.jpg", "images/two.jpg", "images/three.jpg"],
  "carousel": {
    "advance_seconds": 1.6
  }
}
```

Cards use a controlled depth hierarchy, rounded photo crops, clear separation, and a light blur on off-center photos that resolves smoothly as a card approaches center. Each advance follows a finely sampled cosine easing curve, while the interval between advances varies smoothly by up to 22% over the orbit. Wraparound cards fade while they pass behind the stack so the loop remains legible. The carousel is a photographic montage, not a claim that adjacent images share a literal location or time; source licensing and attribution still need review.


## Three-row photo marquee

Use the Studio `photo-marquee` composition for a full-frame, image-led loop. It repeats 3–12 local stills across three equal-size rows; the top and bottom rows deliberately crop at the canvas edges. The rows travel left, right, and left, with a small sinusoidal speed variation that returns to the same phase and velocity at the loop seam. Cards have rounded photo crops, no visible frame, and a broad, soft shadow. Shadow offsets are recomputed from the card position relative to a point light at the center of the canvas, so the cast direction changes smoothly as each image crosses the frame. This composition omits copy so the three moving bands remain the focus.

```json
{
  "id": "photo-marquee",
  "headline": "Photo marquee",
  "layout": "photo-marquee",
  "assets": ["images/one.jpg", "images/two.jpg", "images/three.jpg"]
}
```

Assets stay inside the project or brand asset scope. Review the rendered MP4 for the crop, shadow direction, and loop seam before publication.
