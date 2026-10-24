# Repository agent notes

## Before feature work or delivery
- For backlog work, read `docs/MASTER_PLAN.md` and `docs/ROADMAP_STATUS.json` first; follow their next unblocked task and record verified status there.
- Read the selected brand's `BRAND.md` and `brand.json` before creating a project. For ASTA Energy, use `brands/asta-energy/`.
- The repository's release/privacy and human creative/licensing gates are in `README.md` and the roadmap. Passing tests or CI is not creative approval; do not publish media or bypass an open gate.

## Brand media and renders
- Keep reusable engine code in `src/reels_maker/`; brand identity, media, and project manifests belong under `brands/<slug>/`.
- Manifest media paths resolve from that brand directory, not the shell cwd; do not use traversal to access another brand. Keep footage/audio on disk, not in Python source.
- Before reusing video, run `reels-maker catalog --brand <slug> --json` and inspect `editorial_state` and `overlay_ready`. Unknown/unreviewed media is not automatically clean; finished promos must not get new titles/logos without review.
- New renders go under `renders/<slug>/`; do not treat `legacy/` or `archives/` as active pipeline code. `brands/*/imports/` is ignored quarantine, not approved media.

## Validate and render in order
From the repository root (install with `python -m pip install -e .`; requires Python 3.11+ and FFmpeg/FFprobe):

```sh
reels-maker validate brands/<slug>/projects/<manifest>.json --syntax-only --strict-quality --json
reels-maker validate brands/<slug>/projects/<manifest>.json --root . --json
reels-maker render brands/<slug>/projects/<manifest>.json --root . --strict-quality --json
reels-maker storyboard brands/<slug>/projects/<manifest>.json --video <render.mp4> --output renders/<slug>/qa/<review>.png --json
```

Resolve quality warnings or document an intentional exception before rendering without strict mode. Check exit status and JSON (`status: "ok"`); inspect the actual MP4 with audio and its storyboard before calling a delivery finished. Never guess voiceover word timestamps: `voiceover.sync_marks` must contain manually verified onsets; use `cue-sheet`/strict-quality for timing checks.

## Tests and environment
- CI's full suite command is `python -m unittest discover -s tests -v`; locally, `PYTHONPATH=src:tests python -m pytest tests/ -q` is also used. Focus a unittest with `PYTHONPATH=src:tests python -m unittest <test_module>.<TestCase>.<test_method>`.
- Golden strips are exact-pixel regression fixtures. After an intended visual change, inspect the new strips, then recapture with `PYTHONPATH=src:tests python tests/studio_golden.py --write`; run it without `--write` to verify. A golden update is not creative sign-off.
- macOS icon raster tests need system Cairo (`brew install cairo`). If setting `DYLD_LIBRARY_PATH`, expose only Cairo libraries; adding all of `/opt/homebrew/lib` can substitute Homebrew font libraries and change pixel-exact PIL output. See `docs/ICON_LIBRARIES.md`.
- Some source videos are Git LFS assets (`git lfs pull`); synthetic tests do not require downloading large footage. Archived scripts under `legacy/` may contain machine-specific paths; do not run without porting.

See `docs/AGENTS.md` for the JSON-first CLI contract and `docs/CLI.md` for command and manifest details.
