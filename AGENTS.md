# Repository agent notes

## Before feature work or delivery
- Use `docs/MASTER_PLAN.md` and `docs/ROADMAP_STATUS.json` from the current branch as the backlog source of truth. Older v1 gate summaries are historical; verify them against current files before repeating a claim.
- Keep `main` untouched. Work from a feature branch based on latest `origin/main`; PR #1 is already merged, so do not assume its old draft still exists.
- Verify GitHub visibility before handling client/confidential assets. The last verified state is **PUBLIC**; do not add or push client media, secrets or new licensed assets until the owner’s privacy gate is resolved.
- Human rights, claims, reference-viewing and phone/rubric approvals cannot be substituted by test results or agent-generated metadata.
- Read the selected brand's `BRAND.md` and `brand.json` before authoring a project. For ASTA Energy, use `brands/asta-energy/`.


## Curated professional reference library (mandatory at creative planning)
- Before authoring any new Creative Spec, inspect `docs/REFERENCE_LIBRARY.md` and query the bundled curated library with `python -m reels_maker.creative.reference_library` or `--spec path/to/creative.json` to obtain a cited recipe and anti-pattern list.
- For each authored Creative Spec run `python -m reels_maker.creative.reference_library --spec path/to/creative.json --audit`. The existing creative QA pipeline now incorporates this check automatically. Do not confuse warnings with creative approval; treat obvious placeholders as hard failures.
- Each output requires the existing `docs/REVIEW_RUBRIC.md` human review on an actual device with sound. A passing render, unit test or heuristic score never certifies premium motion design.
- Source examples are external study links only; never copy reference frames, music, brand assets or animations, and never commit downloads of third-party work without rights clearance. Never invent reference timecodes.
- Review data motion against factual source provenance and immutable values. Review flashing in the encoded MP4, not only in JSON metadata.

## Typography quality policy (required)
- Use `docs/PRO_TYPOGRAPHY_SYSTEM.md` and `src/reels_maker/design/typography_profiles.json` for semantic font sizing, leading, tracking, layout spacing and relative hierarchy. `suggested_typography(style, width, height)` provides recommendations scaled to the short side; source design system values are NOT universal social-video requirements.
- Validate intended on-screen copy with `audit_creative_spec()`; Studio `studio-qa` and storyboard QA additionally inspect actual typeset blocks using FreeType font sizes, line counts, line-height, letter spacing and heading/subtitle contrast. Resolve critical-size errors before export; review typography warnings on an actual smartphone.
- Never downscale text into unreadability to fit a crowded layout. Prefer shorter copy, deliberate line breaking and additional shots. Keep intentional Polish diacritics intact, preserve platform UI-safe polygons, and inspect audio/speech holds.
- Accessibility distinction: WCAG 1.4.12 is an adjustable-markup text-spacing override test, not a fixed 1.5 line-height requirement for titles burned into MP4 video.

## Media, paths and renders
- Keep reusable engine code in `src/reels_maker/`; brand identity, media, and project manifests belong under `brands/<slug>/`.
- Rendering and asset operations must go through the documented CLI/API contracts; do not inject a parallel rendering implementation or silently bypass validation.
- Manifest media paths resolve from that brand directory, not the shell cwd; do not use traversal to access another brand. Keep footage/audio on disk, not in Python source.
- Before reusing video, run `reels-maker catalog --brand <slug> --json` and inspect `editorial_state` and `overlay_ready`. Unknown/unreviewed media is not clean; finished promos must not get new titles/logos without review.
- `brands/*/imports/` is ignored quarantine, not approved media. New renders go under `renders/<slug>/`; `legacy/` and `archives/` are reference-only.

## Validate and render in order
From the repository root, install the active checkout (Python 3.11+, FFmpeg/FFprobe required):

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/reels-maker validate brands/<slug>/projects/<manifest>.json --syntax-only --strict-quality --json
.venv/bin/reels-maker validate brands/<slug>/projects/<manifest>.json --root . --json
.venv/bin/reels-maker render brands/<slug>/projects/<manifest>.json --root . --strict-quality --json
.venv/bin/reels-maker storyboard brands/<slug>/projects/<manifest>.json --video <render.mp4> --output renders/<slug>/qa/<review>.png --json
```

Resolve quality warnings or document an intentional exception before omitting strict mode. Check exit status and JSON (`status: "ok"`); inspect the real MP4 with audio and its storyboard before delivery. Never guess voiceover timestamps: `voiceover.sync_marks` needs manually verified onsets; use `cue-sheet` and strict quality for timing. For narrator-led campaigns, manually verify spoken-word onsets and compare them with visual cue positions; missing sync marks provide no automatic audio/text guarantee.

## Tests and environment
- CI's full suite is `python -m unittest discover -s tests -v`. From a fresh checkout create `.venv` and install editable first: integration tests spawn `.venv/bin/reels-maker`. Focus a unittest with `PYTHONPATH=src:tests .venv/bin/python -m unittest <test_module>.<TestCase>.<test_method>`.
- Golden strips are exact-pixel fixtures. After an intended visual change, inspect new strips, then recapture with `PYTHONPATH=src:tests .venv/bin/python tests/studio_golden.py --write`; run without `--write` to verify. A golden update is not creative approval.
- macOS icon raster tests need Cairo (`brew install cairo`). If setting `DYLD_LIBRARY_PATH`, expose only Cairo libraries; adding all of `/opt/homebrew/lib` can substitute Homebrew font libraries and alter PIL antialiasing. See `docs/ICON_LIBRARIES.md`.
- Some source videos are Git LFS assets (`git lfs pull`). Synthetic tests do not need large footage. Archived scripts under `legacy/` may contain machine-specific paths; do not run without porting.

See `docs/AGENTS.md` for the JSON-first CLI contract and `docs/CLI.md` for command and manifest details.
