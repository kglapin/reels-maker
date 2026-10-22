# Reels Maker

One Python/FFmpeg engine for many brands, usable from ChatGPT, Pi, OpenCode
and any noninteractive terminal harness.

**Refactor status:** Work stays on branch `refactor/modular-render-engine`,
within draft [PR #1](https://github.com/kglapin/reels-maker/pull/1).
`main` is unchanged until explicit approval.

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

**Read** `AGENTS.md`, `docs/CLI.md`, and
`brands/asta-energy/BRAND.md` before producing video.

Some external stock videos are stored in Git LFS and require `git lfs pull`.
Synthetic tests run without downloading large footage.

Old green-flash and film-burn animation variants remain to be migrated. Do not
assume brand style metadata alone guarantees pixel-perfect design: verify
rendered typography and platform safe areas visually.

Verify commercial usage rights and current facts before publishing media.
