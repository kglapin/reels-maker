# Carbon in the ordinary Studio engine

## Default behavior

StudioProject construction now normalizes scene copies before the ordinary
QA/build/render/cache path. Scenes without a local policy use productive
Carbon motion. `studio-render` no longer needs the separate Carbon compiler.
An explicit scene profile wins; false/null disables that scene. A project can
set `export.carbon_motion` to false/null, true, or a validated profile object.
Changing export options after construction does not reconfigure the snapshot:
reload/recreate the project for a different policy.

```json
{"export":{"carbon_motion":true}}
```

For an expressive accent use a Studio scene's existing field:

```json
{"carbon_motion":{"mode":"expressive"}}
```

Camera Canvas is not implicitly migrated. Classic FFmpeg/Cairo paths that do
not instantiate StudioProject remain unchanged. Existing explicit scenes stay
author-controlled. Productive is the default, not an automatic classifier of
creative intent; expressive accents remain deliberate choices.

Only the previously implemented adapter's eligible appearance tracks change.
No new movement is added to static nodes; complex/data tracks remain intact.
Colors, font files, copy, data, durations, audio, logos and safe areas are not
replaced. The approved standalone demo is not proof of full Studio parity.

## Additional Carbon element: spacing

The complete 13-token v10 spacing scale is available. Optional
`export.carbon_spacing: true` maps the engine roles xs/sm/md/lg/xl/xxl to
8/16/32/48/64/96 design units. Existing canvas scaling then applies normally.
This is an authored video mapping, not a claim that IBM specifies video pixels.

```json
{"export":{"carbon_spacing":{"md":"spacing-06","xl":"spacing-10"}}}
```

Unspecified roles inherit that mapping. Enabling it intentionally replaces the
six spacing roles, including prior per-style/per-project role values; keep it
off to retain bespoke spacing. Palette, typography and safe zones are untouched.
Source: https://v10.carbondesignsystem.com/guidelines/spacing/overview/

## Additional Carbon element: sequence and stagger

Optional `export.carbon_sequence: true` adds frame-aligned text-role cues only
when the scene has no existing cues. A scene may override/disable this with
`carbon_sequence`. Existing narration/authored cue plans are never overwritten.
Automatic roles are kicker, headline (or amount), body, if corresponding copy
exists. Custom roles can be supplied explicitly.

```json
{"export":{"carbon_sequence":{"gap":0.12,"span":0.5}}}
```

The gap is adapted down to fit the span at actual FPS. Invalid settings or an
unrenderable role count fail, rather than create coincident starts. The .12s
gap is our video adaptation, NOT Carbon's table-row 20ms example. Cue creation
is not speech alignment or proof of sufficient reading hold; run real QA.
Source: https://v10.carbondesignsystem.com/guidelines/motion/choreography/

## Cache, tests and acceptance

Effective scene policies are stored in project.scenes and spacing in project.tokens
before existing cache keys are calculated. The existing engine fingerprint
includes design modules and studio_project.py, so changed code also invalidates
old segments. No cache deletion or fixture recapture is performed here.

The test module separates ten dependency-free policy tests from three native
Studio integration tests. Run both, full regression, and actual MP4 checks.
Default motion intentionally changes pixels: historical golden fixtures may
need independently reviewed, versioned updates. Do not weaken or recapture
fixtures automatically just to make tests pass. Disable the default explicitly
when a project must reproduce legacy motion.

This remains experimental pending native rendering and visual acceptance.
It does not install IBM fonts, copy IBM palettes, implement the full 2x Grid,
change all typography, add rounded motion paths or provide an aesthetic critic.
Carbon expressive typography is a useful next reference, but its UI sizes and
fonts are not imposed on branded social video.
