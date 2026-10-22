# Instructions for ChatGPT, Pi, OpenCode and other terminal harnesses

This repository contains a deterministic, local Python/FFmpeg rendering engine.
Do not merge or write to `main` during refactor; changes belong in the
`refactor/modular-render-engine` branch and draft PR #1.

## Workflow

1. Read the selected brand's `BRAND.md` and `brand.json`. For ASTA Energy:
   `brands/asta-energy/`.
2. Query local assets: `reels-maker catalog --brand asta-energy --json`.
   For each video, inspect `editorial_state` and `overlay_ready`: a finished
   promo must not receive new titles/logos. An unreviewed file is **unknown**,
   not automatically clean; inspect actual frames before reuse.
3. Create/edit a project in `brands/<slug>/projects/`. Manifest paths are
   relative to that brand directory, not to the shell working directory.
4. Run `reels-maker validate <manifest> --syntax-only --strict-quality --json`; fix or explicitly review design warnings.
5. Run `reels-maker validate <manifest> --root . --json`.
6. Run `reels-maker render <manifest> --root . --strict-quality --json` for delivery. If creative intent requires an exception, record the reason before omitting strict mode.
7. Require exit code 0 and a successful JSON response. Generate a contact sheet
   with `reels-maker storyboard <manifest> --video <mp4> --output <png> --json`.
   Inspect the real MP4 with audio and the contact sheet before calling it finished.
   If a voiceover is specified, spot-check the actual spoken words against
   `motion.cue_seconds`, and listen for sidechain pumping or clipped peaks.

Keep brand media and project manifests separate from reusable Python modules.
No agent integration may bypass the CLI and quietly inject another rendering
implementation. New renders go to `renders/<slug>/`; cache is local.
Historical files under `legacy/` and `archives/` are for reference only.

Check media rights and time-sensitive marketing claims before publication.
Other details: `docs/AGENTS.md`, `docs/CLI.md`, `docs/REFACTOR_PLAN.md`.
