# Host-driven creative workflow

This workflow lets the currently active agent/model direct a reel without
configuring a provider, API key, SDK, or network call in `reels-maker`. The host
authors JSON files and invokes the CLI as a normal subprocess. The renderer
validates and renders; the host remains responsible for artistic decisions.

## Hard boundaries

- Read the selected brand's `BRAND.md`, `brand.json`, and `LEARNINGS.md` when
  present. Read `docs/REFERENCE_LIBRARY.md` and retrieve a cited recipe and
  anti-patterns with `python -m reels_maker.creative.reference_library`.
- Use only verified copy/data and appropriately reviewed assets. Never invent
  claims, media rights, or reference timecodes. Public-repo confidentiality gates
  still apply.
- Apply the cited synthesis in `MOTION_DESIGN_RESEARCH.md` together with the
  curated recipes in `REFERENCE_LIBRARY.md`. They are decision prompts, not a
  universal style preset or numerical quality score.
- Fetch actual render evidence before visual critique. If the active model
  cannot receive/read the storyboard or video, report that limitation; do not
  infer that it has seen the render from a manifest or textual description.
- Technical QA is not aesthetic acceptance. Delivery still requires the human
  review rubric on an actual device with sound.

## Host stages

1. **Discover tools.** Run `reels-maker creative-capabilities --json` and
   `reels-maker creative-schema --json`. Use only capabilities advertised by
   this install. The Creative Spec remains the authored scene content; the
   optional decisions file specifies one exact layout/motion decision per scene.
2. **Think before authoring.** Produce three distinct story mechanisms, not
   three preset/color variants. For each, state the promise, how it will be
   visibly paid off with verified material, the hero frame, and the main risk.
   Reject a concept if the required proof/assets do not exist. Pick the strongest
   against the brief; document why the other two are weaker.
3. **Art-direct before animating.** Define the film's visual thesis, focal object,
   framing/hierarchy, image-to-type relationship, palette/type system, and what
   is intentionally still. Design a small set of representative keyframes first;
   compare alternatives on their visual communication, not style adjectives.
   Then block an animatic/beat map: for each scene identify the viewer's task,
   main action, complete readable hold, transition reason and evidence/payoff.
   Vary duration only when the content earns it; do not fill empty story with FX.
4. **Author.** Write a Creative Spec JSON plus a decisions JSON array. Preserve
   exact scene IDs and ordering. Each decision must contain `id`, `layout`, and
   `typography_motion`; optional `layout_reason` is for the decision report.
   For Studio scenes, optional `entrance_presets` maps actual element roles
   (such as `headline` or `body`) to supported motion presets; use `none` when
   an element should remain still. The renderer rejects unknown role names.
   Studio Creative Spec v1 additionally supports `split_lines`, role-timed
   `cues`, and a bounded scene `perspective` camera/path. Prefer these controls
   to adding more unrelated motion presets; preserve an intentional hold.
   Scene content, timing, palette, composition, transitions and camera values
   are authored in the Creative Spec and are subject to its schema/capabilities.
5. **Validate and render.** Run `creative-validate --decisions ... --json`,
    then `creative-compile --decisions ... --json`; review QA and decision source.
    For previews, run `creative-render --decisions ... --output ... --storyboard ...
    --json`. The result includes hashes for the actual MP4 and motion strip,
    sampled scene phases/times, and an `evidence_hash` for critique binding.
    Use project folders and the documented path/asset contracts.
6. **Critique independently.** Provide the real storyboard/motion strip to an
   image-capable host model without the author's rationale. Ask for concrete
   scene/time-specific findings on hierarchy, type, motion, pacing, clarity and
    safe areas. A critique must echo the exact `evidence_hash` and list only the
    modalities (`image`, `video`, `audio`) actually supplied to the model. This
    is a host attestation, not proof the model understood the media. Mark
    unobserved audio, continuous motion, or phone readability as unreviewed.
   Check separately: (a) the keyframes as graphic design, (b) motion/animatic for
   staging, continuity and timing, and (c) final encoded media for audio,
   readability, compression and flashing. A still storyboard cannot certify
   motion or sound. Be explicit about anything the model did not receive.
7. **Revise minimally.** Change only what the evidence supports, preserve facts,
   rights and stable scene IDs, then rerun hard QA and render. Keep a run ledger
   with spec/decision/evidence hashes, findings and exact changes. Limit rounds;
   stop on regressions or stagnation.
8. **Handoff.** Leave human approval pending. Include the final render, actual
   review stills, QA, unresolved limitations and review-rubric checklist.

Example subprocess commands:

```sh
reels-maker creative-validate brands/<slug>/projects/<spec>.json \
  --root . --decisions renders/<slug>/<project>/decisions.json --json
reels-maker creative-compile brands/<slug>/projects/<spec>.json \
  --root . --decisions renders/<slug>/<project>/decisions.json \
  --output renders/<slug>/<project>/compiled.studio.json --json
reels-maker creative-render brands/<slug>/projects/<spec>.json \
  --root . --decisions renders/<slug>/<project>/decisions.json \
  --output renders/<slug>/<project>/preview.mp4 \
  --storyboard renders/<slug>/<project>/storyboard.png --json
```

The host may inspect images using its available vision capability or request a
human review. `reels-maker` does not call the model and does not provide an
automatic aesthetic score.
