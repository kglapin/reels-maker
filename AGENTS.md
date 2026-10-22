# Instructions for ChatGPT, Pi, OpenCode and other terminal harnesses

This repository contains a deterministic, local Python/FFmpeg rendering engine.
Do not merge or write to `main` during refactor; changes belong in the
`refactor/modular-render-engine` branch and draft PR #1.

## Workflow

1. Read the selected brand's `BRAND.md` and `brand.json`. For ASTA Energy:
   `brands/asta-energy/`.
2. Query local assets: `reels-maker catalog --brand asta-energy --json`.
3. Create/edit a project in `brands/<slug>/projects/`. Manifest paths are
   relative to that brand directory, not to the shell working directory.
4. Run `reels-maker validate <manifest> --syntax-only --json`.
5. Run `reels-maker validate <manifest> --root . --json`.
6. Run `reels-maker render <manifest> --root . --json`.
7. Require exit code 0 and a successful JSON response. Open/inspect the MP4
   before reporting it as finished.

Keep brand media and project manifests separate from reusable Python modules.
No agent integration may bypass the CLI and quietly inject another rendering
implementation. New renders go to `renders/<slug>/`; cache is local.
Historical files under `legacy/` and `archives/` are for reference only.

Check media rights and time-sensitive marketing claims before publication.
Other details: `docs/AGENTS.md`, `docs/CLI.md`, `docs/REFACTOR_PLAN.md`.
