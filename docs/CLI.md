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

## Native studio renderer

The studio commands build on the same JSON-first CLI without changing the
legacy renderer. `studio-inspect` resolves tokens, frame timing, layouts and
motion. `studio-qa --strict` returns a nonzero exit code on blocking QA errors.
`studio-render` writes to `renders/<brand>/` unless `--output` is supplied.
Studio commands cache encoded scene segments by default under
`.cache/reels-maker/studio/` in the selected repository root. `--cache-dir PATH`
chooses another location; `--no-cache` disables reuse. Each segment key includes
the render settings, its scene data, resolved visual assets and their size and
modification time. Editing one scene re-renders that scene; a changed global
setting (profile, tokens, fonts or encoder) invalidates all segments. If a scene
has an outgoing transition, its cached segment also depends on the next scene.
## Pixabay audio (music / sound-effects)

MP3 files are served by the content CDN without a Cloudflare challenge
(verified 2026-10-23: valid MP3 frames from cdn.pixabay.com), so once the MP3
URLs are known the downloads run fully unattended. Only the pixabay.com
pages and bootstrap JSON are challenged, and that is what the bridges cover:

- `reels-maker pixabay "query"` tries the direct fetch and, when the
  Cloudflare challenge appears, prints exact guidance instead of retrying
  blindly.
- `--page-file saved.html` parses a page saved from the browser (search
  results or any rendered response served with the page).
- `--tracks-file urls.txt` works from a plain list of CDN MP3 urls copied
  from the browser network tab (one per line, optional `# title` comment);
  because the CDN serves MP3s unattended, this path runs end-to-end without
  a browser.
- `--cookies "cf_clearance=...; ..."` passes the operator's browser cookie
  header for page fetching.
- Downloads require `--pick 2,3` or `--all` and land in
  `brands/<slug>/imports/audio/` — the same git-ignored quarantine area the
  brand scan uses; files inside `media/` are refused.
- Every report carries the Pixabay Content License facts and source URLs;
  publishing a track still requires a human review record in
  `media/asset-library.json` (see the `library` command).

## Public photo/video databases

Search results are candidate records with `rights_status: "unknown"`; search
does not grant reuse rights or download media. Search can combine providers and
continue when one provider is missing credentials or unavailable:

```sh
reels-maker media-search "solar panels" --provider all --kind image \
  --aspect 0.5625 --output candidates.json --json
reels-maker media-search "solar farm" --provider pexels --kind video \
  --limit 12 --output video-candidates.json --json
reels-maker media-search "whoosh" --provider all --kind audio \
  --output sfx-candidates.json --json
```

Image providers are Pexels, Pixabay, Unsplash, Wikimedia Commons and Openverse.
Video search supports Pexels, Pixabay and Wikimedia Commons; audio search
supports Wikimedia Commons and Openverse. Wikimedia needs no API key for any
kind, so it also covers video and sound-effect discovery when no credentials
are configured. Credentials are supplied through `PEXELS_API_KEY`,
`PIXABAY_API_KEY`, and `UNSPLASH_ACCESS_KEY`, either as environment variables
or as `NAME=value` lines in the repository root `.env` file (git-ignored;
real environment variables always win — see `.env.example`). Openverse needs
no account: it runs on the API's anonymous tier (20 requests/minute, 200/day,
enforced locally as well). Setting `OPENVERSE_ACCESS_TOKEN` in `.env` upgrades
to the provider's registered-OAuth limits but is never required.
Inspect the returned `providers` outcomes and each candidate's source, creator,
license and exact `download_url`. The result has `search_status: "ok"`,
`"partial"` or `"unavailable"`; provider errors are included in `providers`
and are not silently treated as empty approved media.
Each candidate also reports `local_download_supported`; an Unsplash URL can be
used only through compliant API hotlinking and is intentionally rejected by
`media-download`.

Downloading requires a separate human-reviewed decision JSON bound to the exact
provider, asset ID, source URL, download URL, reviewer, review date, evidence,
attribution (or an explicit statement that none is required), license and
permitted platforms. Example:

```json
{
  "provider": "wikimedia_commons",
  "asset_id": "123456",
  "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
  "download_url": "https://upload.wikimedia.org/wikipedia/commons/.../Example.jpg",
  "decision": "cleared",
  "reviewer": "Human reviewer",
  "review_date": "2026-10-24",
  "evidence": "rights ticket or review record",
  "attribution": "Crisco 1492, CC BY-SA 4.0",
  "license": "CC BY 4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "allowed_platforms": ["instagram_reels"]
}
```

```sh
reels-maker media-download candidates.json --provider wikimedia_commons \
  --asset-id 123456 --rights-decision rights-review.json \
  --brand <slug> --target-platform instagram_reels --json
```

Downloads are host/IP, redirect, size and time checked; images, videos and
audio files are verified, hashed and staged only in `brands/<slug>/imports/`
quarantine. The
result remains `approval: "not_approved"`; copy nothing into `media/` and do not
publish until editorial and library review is complete. Unsplash is deliberately
not locally downloaded by this command because its API workflow requires
hotlinked image URLs; this checkout does not implement an approved hotlink-based
render path. Openverse external hosts beyond the fixed provider allowlist are
accepted only when the exact item URL is included in a human rights decision and
the resolved host is public HTTPS.

MD-106 live connectivity checks are deliberately opt-in and are never enabled in
CI by default:

```sh
PYTHONPATH=src:tests REELS_MAKER_LIVE_MEDIA_TESTS=1 \
REELS_MAKER_LIVE_MEDIA_PROVIDER=wikimedia_commons \
.venv/bin/python -m unittest test_media_live_optin -v
```

The search smoke test does not download bytes or clear rights. A real acquisition
smoke additionally requires `REELS_MAKER_LIVE_MEDIA_DOWNLOAD=1`, the exact
`REELS_MAKER_LIVE_ASSET_ID`, and a reviewed JSON decision path in
`REELS_MAKER_LIVE_RIGHTS_DECISION`; it stages only into a temporary directory.
Do not add credentials or a download-decision file to the repository.

## Asset-library rights gate

```sh
reels-maker library brands/<slug>/media/asset-library.json --json
```

The command's top-level `status: "ok"` means the manifest was parsed and
validated. Check `library.delivery_ready` separately: `false` means one or more
assets still have unknown/blocked rights or are not editor-reviewed. Never
publish merely because the JSON command succeeded; source/license metadata and
human review remain required.

For legacy kinetic manifests, `kinetic-render` keeps Cairo as its default; opt
into the shared studio engine with `--engine studio` during migration:

```sh
reels-maker studio-inspect brands/asta-energy/projects/asta-motion-system-demo.json --profile review --json
reels-maker studio-qa brands/asta-energy/projects/asta-motion-system-demo.json --profile review --strict --json
reels-maker studio-render brands/asta-energy/projects/asta-motion-system-demo.json --profile final --supersample 1 --json
reels-maker storyboard brands/asta-energy/projects/asta-motion-system-demo.json --video renders/asta-energy/asta-motion-system-demo-final.mp4 --output renders/asta-energy/qa/studio-storyboard.png --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --title-engine studio --json
reels-maker kinetic-render brands/asta-energy/projects/legacy-kinetic.json --engine studio --json
```

The kinetic adapter is explicitly opt-in because it changes composition and
motion; global legacy header/logo placement may need per-scene adjustment.
The default `kinetic-render` invocation continues to use Cairo.

Classic video `render --title-engine studio` generates animated transparent
title overlays from the scene graph and composites them over original moving
footage. FFmpeg still owns trim, format normalization, transitions, cache and
audio. Legacy Pillow title cards remain the default until visual parity is
reviewed.

Studio export profiles are `preview` (360×640/20 fps), `review`
(720×1280/30 fps), `final` (1080×1920/30 fps) and `high-motion`
(1080×1920/60 fps). Pass the same profile to render and storyboard when it
differs from the manifest's export profile. The storyboard command checks MP4
dimensions, FPS, frame count and audio structure before sampling real frames.
See [MOTION_DESIGN_SYSTEM.md](MOTION_DESIGN_SYSTEM.md) for the full studio
manifest and QA contract.

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
Use `--jobs 1..8` based on available CPU and memory for classic video
renders. Studio rendering uses `.cache/reels-maker/studio/` by default;
`--cache-dir` selects another location and `--no-cache` forces a full rebuild.
Studio cache entries are scene-local and include resolved visual asset metadata.

Do not assume `brand.json` font-family guidance automatically installs or
embeds a font. The renderer resolves `branding.font_family` /
`identity.typography.primary` to an installed `<Family>-Regular.ttf` /
`<Family>-Bold.ttf` (for example a Google Fonts download in
`~/Library/Fonts`), then brand `fonts/` directories, then compatible system
fallbacks. Explicit `branding.font_regular`/`font_bold` or
`identity.typography.regular`/`bold` file paths take precedence; font
licensing remains the operator's responsibility.

## Brand-safe typography and performance timings

The renderer uses optional `branding.safe_areas` from the individual project to position its logo and text. The brand preset never imposes resolution, aspect ratio, frame rate or platform-specific margins. `branding.font_family` resolves an installed family by name (`Open Sans`, `Montserrat`, `JetBrains Mono`, ...) to `<Family>-<Weight>.ttf` files in the user/system font directories, otherwise DejaVu Sans (no bundled fonts). Explicit `font_regular`/`font_bold` file paths can override font discovery; font licensing is the operator's responsibility.

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

For every standard 9:16 vertical Reels project, authored text and illustrations
must stay inside a shared content zone: 7.5% side margins, 9% at the top and
16% at the bottom. Full-bleed backgrounds and positions reached only while an
element is moving are exempt. Studio QA checks authored geometry before motion
tracks are sampled; Camera Canvas uses the same zone for its photo and text.

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

## Agent-safe media discovery

The `reels-maker catalog --brand asta-energy --json` response now includes
`editorial_state` and `overlay_ready` for video footage when its status has
been reviewed. Values are `finished_promo`, `clean_source` or `unreviewed`.
A file marked `finished_promo` can already carry rendered logos or captions:
do not add new motion typography over it. `overlay_ready=null` means unknown;
it is **not** consent to reuse. The categorization is maintained per brand in
`media/asset-reviews.json` from inspected frames. A strict-quality render
raises `source_is_prebranded` if new titles or inherited logo are added to
annotated finished promo footage. When intentionally reusing old video
without any new overlay, set `branding.logo` to `null` and omit titles;
publication still requires licence and content review.

## Precise narration-aligned animation cues

Use `motion.cue_seconds` with scene-local timestamp values, or
`motion.cue_frames` with integer frame offsets; choose exactly one.
These are explicit cues, not AI-estimated transcript timestamps. The engine
quantizes seconds to the output FPS and validates layer names, fade duration
and a minimum 0.55s fully revealed hold. `headline-0` refers to the first
styled `title.headline.runs` segment; `headline` targets a plain string.
`logo`, `accent`, `kicker`, `body` and `footer` are supported. Uncued
elements retain the existing stagger. See `docs/MOTION_DESIGN.md`.

## Separate narration and music tracks

`voiceover` is a first-class, independent audio input; it is **not** part of
the brandbook and does not have to be embedded in a background-music file.
An editor can use verified narration timestamps to schedule visual
`motion.cue_seconds` from the beginning of each scene.

```json
{
  "music": {
    "file": "media/audio/score.wav",
    "volume": 0.30,
    "fade_out": 0.4,
    "ducking": "sidechain"
  },
  "voiceover": {
    "file": "media/audio/narrator.wav",
    "start": 0,
    "offset_seconds": 0.20,
    "volume": 1.0
  }
}
```

`voiceover.start` trims the source recording; `offset_seconds` delays the
narration relative to the **final video timeline**. A short voice recording
ends in silence; the engine never loops narration. When both voice and music
are present, optional `music.ducking = "sidechain"` reduces soundtrack volume
in response to the narrator. It uses moderate FFmpeg compressor settings, a
gentle release and a 0.95 peak limiter before 48kHz AAC export. With
`ducking: "off"` (default) no sidechain compression is applied; a limiter
still prevents clipped sums. No background soundtrack, timing or AI voice is
added automatically. Validate listening quality before publishing.

Warning: `voiceover.offset_seconds` is **global output time**;
`motion.cue_seconds` refers to the start of the **individual scene**,
including any scene-overlap implications. Editors must align them on the
actual timeline and re-check timing when changing transitions.

## Inspect the actual global visual cue timeline

`reels-maker cue-sheet <manifest> --json` yields a scene-by-scene
timing report with exact frame indices and seconds for every text role.
Use `--output renders/qa/cues.json` to save an editable-friendly machine
report. Positions reflect real overlap from `xfade` and the separate global
voiceover offset; source-transcript timestamps are not guessed.

## Strict validation of narrator word cues

To guard against an edit that makes text appear too early or late relative to
the *actual* narrator, add manually spotted word timestamps from the **original
voice recording**. Markers are never guessed by speech recognition:

```json
{
  "voiceover": {
    "file": "media/audio/narrator.wav",
    "start": 0.20,
    "offset_seconds": 0.10,
    "sync_marks": [
      {
        "scene": 2,
        "role": "headline-1",
        "source_seconds": 2.18,
        "tolerance_frames": 2
      }
    ]
  }
}
```

`scene` is 1-based. `source_seconds` points into the original audio file,
**before** `voiceover.start` trims it. The expected final-timeline time is
`source_seconds - voiceover.start + voiceover.offset_seconds`; meanwhile,
the visual text's global frame accounts for all intervening xfade overlaps.
If the absolute difference exceeds `tolerance_frames` (default 2, range
0–6), `cue-sheet` reports `narration_cue_drift`; `--strict-quality`
refuses the campaign before render. Markers pointing outside the final
timeline, to missing text runs, or beyond the WAV source duration also fail
validation. The cue-sheet report now includes `sync_marks`, `delta_frames`,
and `delta_seconds`, making editing decisions auditable.

This checks **declared** manually verified word times against programmed
visual entrances. It does not prove a WAV actually contains that word, or
replace listening to the final file. When narration is retrimmed, re-check
the original source timestamps. Never silently treat unmarked speech as
aligned.

## Fast Polaroid photo burst

Use a `polaroid_burst` scene to pop in several photos as overlapping white
Polaroid cards. Each card receives a deterministic random position and a
gentle left or right tilt (about 4.5–7 degrees by default), enters with a quick
scale settle, and remains in the stack. The cards use a diffuse, soft shadow.
A brief white flash is placed above the cards at each shot. If
`shutter_sound` is set, the Studio loader creates one SFX event on the same
frame as each flash; the existing audio mixer adds it to the exported AAC.

```json
{
  "type": "polaroid_burst",
  "duration": 3.2,
  "background": {"kind": "solid", "color": "#181525"},
  "polaroid_burst": {
    "photos": [
      "media/photos/shot-01.jpg",
      "media/photos/shot-02.jpg",
      "media/photos/shot-03.jpg",
      "media/photos/shot-04.jpg",
      "media/photos/shot-05.jpg"
    ],
    "shutter_sound": "shared://audio/polaroid-shutter-click.mp3",
    "shutter_gain_db": 2,
    "interval": 0.20,
    "first_at": 0.06,
    "rotation_degrees": 7,
    "card_width_fraction": 0.58,
    "spread_x": 0.13,
    "spread_y": 0.15,
    "seed": 12
  }
}
```

Photo and sound paths resolve inside the selected brand folder by default.
Use `shared://<path>` for an app-level asset under `shared_media/`; the shared
resolver rejects paths that escape that directory. This lets any brand use the
same maintained sound file without copying it into each brand folder. `photos`
accepts 2–16 PNG, JPG or WebP stills. The interval, entrance and flash are
quantized to the project FPS; the scene must leave enough time for the final
flash and a short hold. Keep `seed` fixed to reproduce a reviewed arrangement.
The effect uses the supplied SFX path and does not add music automatically.
