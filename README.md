# Reels Maker

A Python + FFmpeg rendering engine for vertical video. Usable from normal
shells, ChatGPT, Pi, OpenCode and other terminal-driven agents.

**Current status:** refactoring in progress on the
`refactor/modular-render-engine` branch and draft [PR #1](https://github.com/kglapin/reels-maker/pull/1).
Do not merge into `main` until real-media regression and legacy FX parity
have been verified.

## Install

Requirements: Python >=3.11, FFmpeg with `libx264` and FFprobe, plus optional
Git LFS for externally sourced media.

```sh
python -m pip install -e .
reels-maker doctor --json
reels-maker catalog --root . --json
```

## Build a video from a manifest

```sh
reels-maker validate projects/asta-rush-demo.json --syntax-only --json
reels-maker validate projects/asta-rush-demo.json --root . --json
reels-maker render projects/asta-rush-demo.json --root . --jobs 2 --json
```

Success prints machine-readable JSON with an absolute `output` path, frame
dimensions, duration and cache statistics. Failure exits with a nonzero code
and a structured JSON error on stderr. No interactive input is required.

The `catalog` command lists video/audio files without opening their decoders
unless `--probe` is supplied. It also detects Git LFS pointer files. Use
`git lfs pull` when the required stock footage is not yet hydrated.

## Internals

- `src/reels_maker/spec.py`: validated JSON project schema.
- `src/reels_maker/media.py`: single-pass source validation and metadata.
- `src/reels_maker/cards.py`: safe-area text and PNG brand overlays.
- `src/reels_maker/renderer.py`: parallel cached scene encoding, cumulative
  frame-accurate timing, stream-copy assembly and audio multiplexing.
- `src/reels_maker/cli.py`: stable terminal interface.
- `src/reels_maker/catalog.py`: fast asset discovery for agents.
- `projects/`: reusable animation configurations.
- `tests/`: unit and synthetic-video integration tests.
- `engine/scripts/`: original legacy scripts retained for compatibility
  and visual comparison (not migrated yet).

Source clips, reusable assets and finished historical exports remain available
in the repository for now. New output and cache files are ignored by Git.

## Performance model

Unchanged video scenes are restored from local cache. FFmpeg normalizes only
cache misses, encodes independent scenes concurrently, concatenates them with
stream copy and adds audio in the final step without re-encoding the picture.
Frame counts are calculated from cumulative cut boundaries to avoid beat drift.
Use distinct output paths for concurrent agent jobs.

The existing large media repository can be cloned selectively using Git
partial clone/sparse checkout; however, each media blob still needs downloading
when that specific file is rendered. Avoid unconditional `git lfs pull` for
stock assets that a given video does not use.

## Known limitations

Historical film-burn and green-flash transition treatments are not yet migrated;
legacy manifests are **functional baselines**, not pixel-identical replacements.
Automated synthetic tests do not prove production footage, design or music
licensing. Validate claims and legal attributions before publication.

Detailed agent contract: [docs/AGENTS.md](docs/AGENTS.md).
CLI and manifest reference: [docs/CLI.md](docs/CLI.md).
Implementation tracker: [docs/REFACTOR_PLAN.md](docs/REFACTOR_PLAN.md).
