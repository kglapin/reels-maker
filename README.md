# Reels Maker

One Python/FFmpeg engine for many brands and video formats, usable from ChatGPT, Pi, OpenCode
and any noninteractive terminal harness.

**Refactor status:** `refactor/modular-render-engine` was merged through
[PR #1](https://github.com/kglapin/reels-maker/pull/1) on 2026-10-23. The
separate native motion-studio prototype is on local branch
`feat/motion-design-system-20261023`; it has not been pushed or merged.

## Canonical 1.0 completion plan

The comprehensive, ordered backlog is
[docs/MASTER_PLAN.md](docs/MASTER_PLAN.md), with a compact machine-readable
[milestone status](docs/ROADMAP_STATUS.json). Use these for all follow-up
work. A passing CI run is not a creative sign-off. The repository **must
remain private**. A live GitHub check on 2026-10-23 reported `PUBLIC`, contrary
to this policy. An owner must restore/confirm privacy; do not push the local
prototype or media while this blocker is open. PR #1 is already merged; that
does not approve the prototype or release.


## Professional typography and readable social video

Typographic roles, evidence-based line-height/tracking/spacing guidance,
format-responsive type scales and measured quality checks:
[docs/PRO_TYPOGRAPHY_SYSTEM.md](docs/PRO_TYPOGRAPHY_SYSTEM.md).
The [machine-readable profiles](src/reels_maker/design/typography_profiles.json)
specify editorial, dynamic-ad and data-storytelling hierarchies.
Existing `creative-qa`, Studio `studio-qa` and scene storyboard QA now
include corresponding typographic preflight checks (long headlines, actual
font size, leading, letter spacing, line counts and weak text hierarchy).
Layout-safe-zone and contrast checks remain active; consult the document for
video-specific adaptations vs published UI/web source sizes.

```python
from reels_maker.design.typography_policy import suggested_typography
print(suggested_typography("editorial-premium", 1080, 1920))
```

## Curated motion reference and anti-slop preflight

Professional craft references and production recipes are documented in
[docs/REFERENCE_LIBRARY.md](docs/REFERENCE_LIBRARY.md) and stored as
[reference_data/library.json](src/reels_maker/creative/reference_data/library.json).
They provide curated creative direction, negative examples, links to original
studios and data-visualization patterns; no third-party video bytes are stored.

```sh
python -m reels_maker.creative.reference_library
python -m reels_maker.creative.reference_library --spec examples/creative-engine-editorial-demo.json
python -m reels_maker.creative.reference_library --spec examples/creative-engine-editorial-demo.json --audit
```

`creative-qa` integrates the deterministic preflight issues with existing
technical quality checks. Only unfinished placeholder copy is a new hard
failure; compositional slop risks are warnings. Manual review of video,
sound, rights and factual claims is still required. Reference-board footage
and ideas must not be copied or imported as media assets.

## Architecture

- `src/reels_maker/` — shared Python/FFmpeg engine; no per-brand copies.
- `brands/<slug>/brand.json` — machine-readable colors, logo and defaults.
- `brands/<slug>/BRAND.md` — human/agent-facing visual editorial guidelines.
- `brands/<slug>/media/` — footage, licensed stock, audio and effects.
- `brands/<slug>/projects/` — reusable JSON animation manifests.
- `renders/<slug>/` — new MP4 output (ignored by Git).
- `renders/<slug>/archive/` — preserved historical reference exports.
- `archives/` and `legacy/` — previous intermediate media and historical
  project scripts; not part of the active video pipeline.
- `.cache/reels-maker/` — reusable encoded segments (ignored by Git).

## Quickstart

Requires Python 3.11+, FFmpeg with FFprobe and `libx264`:

```sh
python -m pip install -e .
reels-maker doctor --json
reels-maker catalog --brand asta-energy --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --syntax-only --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --root . --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --root . --jobs 2 --json
```

An agent needs only a brand folder, selected project manifest and source media.
Renders reuse cached, encoded segments and concatenate without re-encoding.
FFmpeg is the rendering backend; there is no hosted model dependency.

## Native motion-design studio (experimental)

The separate Pillow-based studio engine is available without changing the
legacy `render` or `kinetic-render` paths. It adds shared layout recipes,
measured typography, five reusable style systems, retained scene graphs,
cue-aware motion, asset provenance checks, selective one-word image-negative
type and deterministic visual QA:

```sh
reels-maker studio-inspect brands/asta-energy/projects/asta-motion-system-demo.json --profile review --json
reels-maker studio-qa brands/asta-energy/projects/asta-motion-system-demo.json --profile review --strict --json
reels-maker studio-render brands/asta-energy/projects/asta-motion-system-demo.json --profile final --supersample 1 --json
reels-maker storyboard brands/asta-energy/projects/asta-motion-system-demo.json --video renders/asta-energy/asta-motion-system-demo-final.mp4 --output renders/asta-energy/qa/asta-motion-system-demo.png --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --title-engine studio --json
reels-maker kinetic-render brands/asta-energy/projects/legacy-kinetic.json --engine studio --json
```

Profiles: `preview` (360×640/20 fps), `review` (720×1280/30 fps), `final`
(1080×1920/30 fps) and `high-motion` (1080×1920/60 fps). See
[docs/MOTION_DESIGN_SYSTEM.md](docs/MOTION_DESIGN_SYSTEM.md) for architecture,
manifest contract and QA limits. The included ASTA demo is a design-system
sample with explicitly illustrative numbers, not an approved advertisement.
Its stock clips are rights-documented; music is omitted until its publication
licence is verified. An automated QA pass is not human creative approval.
`kinetic-render` still defaults to its legacy backend; `--engine studio` opts a
legacy kinetic manifest into the new shared scene/layout/QA engine while parity
work proceeds. Classic video `render` can opt into studio-generated animated
title overlays with `--title-engine studio`; FFmpeg still decodes and preserves
the original moving footage. Both legacy renderers remain defaults until
visual parity is reviewed.

**Read** `AGENTS.md`, `docs/CLI.md`, and
`brands/asta-energy/BRAND.md` before producing video.

Some external stock videos are stored in Git LFS and require `git lfs pull`.
Synthetic tests run without downloading large footage.

Old green-flash and film-burn animation variants remain to be migrated. Do not
assume brand style metadata alone guarantees pixel-perfect design: verify
rendered typography and platform safe areas visually.

Verify commercial usage rights and current facts before publishing media.

## Independent output formats and brandbook PDF

The brand sets **identity**, not output dimensions or a platform preset. Width,
height, aspect ratio and FPS are configured independently in each project
manifest; optional safe areas are also selected per project. A single brand can
render portrait, landscape and square animations without changing brand.json.

```sh
python -m pip install -e '.[pdf]'
reels-maker brandbook --brand asta-energy --json
```

The generated two-page PDF focuses on logo, palette, typography and usage
rules. It does **not** prescribe a video size or aspect ratio.

## Discover brand styling directly from a public website

Install the optional website scanner and PDF exporter:

```sh
python -m pip install -e ".[brand]"
reels-maker brand-scan https://www.example.com --brand example --json
```

The scanner prepares a reviewable `website-report.json`, saves logo
candidates under `brands/example/imports/assets/` and creates
`renders/example/brandbook-proposal.pdf` (2 pages). It **never** overwrites
accepted `brand.json`. Review the PDF and evidence before activating the
suggested identity. See [docs/BRAND_SCAN.md](docs/BRAND_SCAN.md).
