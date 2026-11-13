# Carbon v10 Motion integration (experimental)

This implements Carbon's six source cubic-bezier curves and six duration
constants in `motionkit.carbon`, not merely reference URLs. No npm dependency
is required. IBM's source is the v10 overview linked in the module.

## Actual render integration

A scene opts in with `"carbon_motion": {"mode": "productive"}`. The shared
`components.scenes.build_scene` boundary applies the profile to actual native
Keyframe/Track objects. The renderer and scene QA therefore receive the same
modified graph. Without this field (or with null), behavior is unchanged.
This is not automatic replacement of all existing brand motion.

Modes: productive and expressive. Phases: standard, entrance, exit. By default
opacity direction selects entrance/exit; transforms returning to neutral use
entrance, and other simple transforms use standard. Override ambiguous cases
explicitly per role. Do not treat this heuristic as semantic scene analysis.

Only nonconstant two-key appearance tracks are modified. Data/counter/progress
tracks, multi-key paths and complex choreography are preserved and listed in
`built.meta.carbon_motion.skipped`. No new motion is invented for static nodes.
The adapter preserves values and, by default, timings. It changes both keys'
easing and native cubic-bezier params, not only metadata. Reports record each
modified role/property and explicitly withhold visual approval.

## Compile a Creative Spec

```sh
python -m reels_maker.motionkit.carbon input.creative.json --root . --expressive-shot hook --output renders/brand/project/carbon.studio.json
```

Use actual brand/project paths and a real shot ID instead of the placeholders.
This calls the previously added craft compiler, retains its QA gate and
produces a normal Studio manifest with productive scenes and selected
expressive accents. `--allow-warnings` exports for review only. Existing
outputs and the input cannot be overwritten.

For a source-only demo with no external media:

```sh
reels-maker studio-qa examples/carbon-motion-demo.json --profile review --strict --json
reels-maker studio-render examples/carbon-motion-demo.json --profile review --json
```

These commands are instructions, not evidence that an MP4 was rendered.

## Optional duration tokens

Per-scene example:

```json
{"carbon_motion": {"mode": "productive", "minimum_hold": 0.8,
  "roles": {"headline": {"mode": "expressive", "phase": "entrance",
    "duration_token": "slow-01", "film_scale": 1.5}}}}
```

An explicit nonempty roles map limits the adapter to those exact node roles;
unknown roles fail instead of silently doing nothing. Source values are
fast-01=70, fast-02=110, moderate-01=150, moderate-02=240, slow-01=400,
slow-02=700 milliseconds. These are UI tokens, NOT universal film durations.
`film_scale` and `minimum_hold` are authored film adaptations, not IBM rules.
Retimed intervals round up to whole frame durations at actual export FPS;
start times and values are preserved. Invalid settings, scene overflow or
consumed minimum hold fail atomically before replacing any tracks.

## Tests and limits

`tests/test_carbon_motion.py` separates eight isolated policy/adapter tests
(using explicit fixtures) from three native engine/builder integration tests.
Run the whole module and full regression suite in the installed checkout.
A fixture-class pass is not a native renderer/integration or MP4 pass.

This stage does not implement Carbon typography, grid/spacing tokens, rounded
orthogonal paths, full semantic/spatial choreography, cross-scene shared
objects, a multimodal critic or automatic creative approval. Added search/note
nodes attached after the central builder do not receive the scene adapter.
Keep brand colors/fonts and manually review actual video, sound and safe zones.
All outputs remain experimental until independent visual acceptance.

Sources:
- https://v10.carbondesignsystem.com/guidelines/motion/overview/
- https://v10.carbondesignsystem.com/guidelines/motion/code/
- https://v10.carbondesignsystem.com/guidelines/motion/choreography/
