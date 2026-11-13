# Executable craft recipes (experimental foundation)

## What is implemented

`creative.professional_direction` is an additive, opt-in entry point. It
selects six renderer-backed recipes, preserves explicit author choices,
uses a coherent copy entrance and emits actual Studio `cues` and
`entrance_presets`. It calls the existing Creative Spec validator, compiler
and creative QA. It is not a parallel renderer and does not change legacy
`creative-compile`, `plan_shots`, Studio manifests or Camera Canvas defaults.

Recipes: editorial-statement, photo-proof, metric-proof, data-story,
portfolio and quiet-resolution. `recipe_catalog()` exposes prerequisites,
invariants, original-source guidance and experimental status. No recipe is
self-marked visually approved. Numeric values alone never cause selection
of the renderer's currency-formatted amount scene.

## Compile and review

```sh
python -m reels_maker.creative.professional_direction input.creative.json --root . --output renders/brand/project/craft.studio.json
reels-maker studio-qa renders/brand/project/craft.studio.json --profile review --strict --json
reels-maker studio-render renders/brand/project/craft.studio.json --profile review --json
```

Use the appropriate real brand/project path, not the literal placeholders.
Media still goes through existing scoped asset checks. Compilation rejects
QA errors and, by default, warnings. `--allow-warnings` creates a review
manifest only, with explicit warnings in the adjacent craft report. Existing
files are never overwritten. A compiled result is not publication approval.

API: `compile_professional_spec(spec, source_dir=..., root=...)` returns a
normal Studio manifest and report. The report includes `craft_decisions`,
QA, source links and `visual_approval: null`. Recipes do not invent numbers,
contacts or assets; existing renderer defaults still need content review.

Reading hold uses authored estimates (16 characters/s and a .75s entrance
allowance), not universal standards or measurements of final node tracks.
Do not shrink text to clear a warning: shorten copy, add time, or split shots.
Inspect real MP4 cues and builder-specific roles before creative acceptance.

## Critic calibration

`calibration_report(expected, predicted)` compares A/B labels for identical
case IDs and rejects missing/extra predictions. Expected labels require
independent review. Use held-out real clips, randomized A/B sides, good
alternatives and deliberately degraded examples. It does not run a model,
persist preferences, produce labels or certify aesthetic quality.

## Review interpretation

Use REVIEW_RUBRIC.md, but evaluate intentional expressive movement in its
style/brand context: overshoot is not intrinsically wrong. Owner bans can
still apply. Synchronize meaningful events with speech/music; not every
movement must hit a beat. These are review clarifications, not automated
changes to the existing rubric or its acceptance thresholds.

Source principles (not copied animation frames or universal film timings):
- https://carbondesignsystem.com/guidelines/motion/overview/
- https://m1.material.io/motion/choreography.html
- https://developer.apple.com/design/human-interface-guidelines/motion

## Status, tests and remaining work

All six recipes are experimental pending actual MP4, mobile, audio, rights
and independent visual review. Run `python -m unittest discover -s tests -p
test_professional_direction.py -v` and then the full repository suite.
The test module separates 13 pure policy tests from repository integration
tests. A pure-class run must not be reported as full integration/render QA.

This first foundation does NOT implement a multimodal critic, automatic
visual repair, persistent taste learning, approved golden MP4s, a rendered
negative-example corpus, advanced morphs, or verified shared-object grammar.
`craft.connection` is planning metadata and explicitly does not verify
continuity. Future default-pipeline integration must follow regression and
visual approval, not just successful compilation. No external assets,
secrets or client media are introduced by this change.
