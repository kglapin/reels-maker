# Carbon Motion in reels-maker

The ordinary StudioProject path now inherits productive Carbon motion by
default. See CARBON_ENGINE_DEFAULTS.md for the current policy, overrides,
spacing and sequence/stagger integration. The low-level scene adapter still
requires an effective `carbon_motion` object; StudioProject supplies it on
scene copies before QA/render/cache. Direct builder calls without that field
remain unchanged.

## Profiles and override

Modes: productive and expressive. Phases: standard, entrance, exit. The six
source curves and six duration tokens live in motionkit/carbon.py. Native
cubic-bezier Keyframes/Tracks are modified, not just metadata. Only simple,
nonconstant two-key appearance tracks are affected. Data/counters/progress
and complex choreography are preserved and reported as skipped.

A scene can use `"carbon_motion":{"mode":"expressive"}` or disable motion
with false/null. Project default: `"export":{"carbon_motion":false}` disables
implicit Carbon while retaining any explicitly opted-in scene. Camera Canvas
is not implicitly migrated. Colors, fonts, media and source numbers stay owned
by the brand/project.

Timing remains authored unless a role explicitly selects a duration token.
film_scale and minimum_hold are video adaptations, not Carbon UI standards.
Raw source durations: 70/110/150/240/400/700ms. Retimed intervals round up to
frames and are validated before track replacement. See the engine policy
reference for opt-in spacing and sequence controls.

## Demo and acceptance

```sh
reels-maker studio-qa examples/carbon-motion-demo.json --profile review --strict --json
reels-maker studio-render examples/carbon-motion-demo.json --profile review --json
```

The separate Carbon compiler remains available, but is not required for
ordinary Studio rendering. Source-only demo commands are not render evidence.
Tests/test_carbon_motion.py covers isolated and native adapter contracts;
tests/test_carbon_defaults.py covers default policy and Studio integration.
Run native tests, full regressions, golden comparisons and MP4 review before
claiming full integration quality. The approved standalone curve demo is not
full-engine acceptance. No fonts, media or third-party assets are imported.

This is not the complete Carbon design system: full grid, responsive
expressive typography, rounded orthogonal paths, shared-object transitions
and an aesthetic critic are not claimed as implemented.

Sources:
- https://v10.carbondesignsystem.com/guidelines/motion/overview/
- https://v10.carbondesignsystem.com/guidelines/motion/choreography/
- https://v10.carbondesignsystem.com/guidelines/spacing/overview/
