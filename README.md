# Reels Maker

Portable Python and FFmpeg rendering engine for vertical social videos.

**Status:** active refactor. The original source footage and `engine/scripts/` remain in place.
All changes are accumulated on branch `refactor/modular-render-engine` in a single draft PR.
This engine currently implements **cuts, crop/pad, static branded title overlays and music**.
Historical green-overlay / beat-montage variants are not yet ported; the older scripts remain the source of truth for those effects.

## Install

Requirements: Python 3.11+, FFmpeg with `ffprobe`, `libx264`, and DejaVu Sans fonts.
On macOS, Linux or Windows install FFmpeg system-wide and ensure the executables are on PATH.

```sh
python3 -m pip install -e .
reels-maker doctor --json
```

## Non-interactive terminal interface

Run from the repository root, or set `--root /absolute/media/root`.
Paths inside the manifest are **relative to that root**, not to the manifest.

```sh
reels-maker validate projects/asta-rush-demo.json --syntax-only --json
reels-maker validate projects/asta-rush-demo.json --root . --json
reels-maker render projects/asta-rush-demo.json --root . --json
reels-maker render projects/asta-rush-demo.json --root . --output output/demo.mp4 --json
reels-maker inspect output/demo.mp4 --json
```

You can also use `python3 -m reels_maker render ...` instead of the installed command.

- Standard output is a single JSON object with `schema_version: 1`.
- Errors print a JSON object to standard error and terminate with exit code 2.
- `doctor` exits with code 3 if FFmpeg / FFprobe executables are unavailable.
- Render output contains `output`, `duration`, `cache_hits`, `cache_misses` and `status`.
- The CLI never asks for input, starts a daemon or modifies Git.
- It is safe for harnesses to parse the final JSON response; shell exit code signals success/failure.
- Cache lives in `.cache/reels-maker/`. Unchanged shots are not re-encoded.
- An isolated scratch directory is used for each render invocation. Export is atomic.
- `--no-cache` forces a cold render; `--cache-dir` sets the cache directory.
- `validate --syntax-only` works without local media or FFmpeg binaries.
- External source videos under `engine/assets/commons/` require `git lfs pull`.

## Harness-compatible call

Pi, OpenCode, ChatGPT tooling, CI runners and other agents can invoke exactly the same contract:

```sh
reels-maker render projects/asta-rush-demo.json --root "$PWD" --json
```

Read the stdout JSON only if the subprocess exits with status zero.
Use the returned `output` path as the result artifact; never infer a filename.
See [docs/AGENTS.md](docs/AGENTS.md) for agent execution constraints.

## Development

```sh
python3 -m unittest discover -s tests -v
```

The baseline tests are fast and do not require the original large movie files.

## Source rights

Some source movies are covered by separate licenses. Review
`engine/assets/stock_credits.txt` before publishing any adapted production.
Do not assume the project files are cleared for redistribution.
