# Kinetic Typography — creative direction and variation rules

Status: **normative creative guidance** for planning and evaluating Reels Maker scenes. This document does not imply that all described animation primitives are currently implemented.

## Objective

Create typography that feels directed rather than templated. **Vary the mechanism of text animation between scenes, while keeping a shared design language.** Different does not mean random. Every move should express the meaning of a phrase and serve the visual narrative.

The approved editorial kinetic typography v4 demo is a **directional reference**, not a recipe to reproduce identically for every project.

## Rules of composition

1. **Start with information hierarchy**: identify the hero word/phrase, secondary text and intended reading order. Make one key message dominant in each beat.
2. **Choose motion for its narrative purpose**: reveal = discovery, convergence = connection, scale = emphasis, displacement = progression, replacement = iteration/comparison.
3. **Use genuine variety**: in a sequence of four primary typography scenes, aim for at least three meaningfully distinct entrance/transition mechanisms, unless repetition conveys a deliberate motif. This is a creative review target, not a hard invariant.
4. **Keep the shared visual grammar**: consistent fonts, palette, spatial rhythm, easing family, density and baseline alignment. Distinct methods can share the same sense of weight and timing.
5. **Change more than direction**: four slides from the bottom with different stagger values are still the same effect. Variation must involve the animated property, masking structure, temporal grouping or interaction with other objects.
6. **Contrast movement with stillness**: give each key phrase a readable hold. Avoid constant letter motion, multiple simultaneous attention targets and gratuitous camera movements.
7. **Never reuse the same trick mechanically across consecutive scenes**. When two adjacent scenes use the same mechanism, require an explicit intentional repetition (e.g. build-up, list, rhythm).
8. **Prefer meaningful interactions**: text should influence or be influenced by a photo, icon, camera or next scene where the concept calls for it. Do not overlay unrelated movement.
9. **Avoid AI-slop defaults**: no side rails, arbitrary underlines, bouncing every word, rotating individual letters without semantic purpose, glow/gradient clutter, meaningless kinetic separators or every-word colored emphasis.
10. **Protect legibility** at the start, during maximum movement and on the settling frame. Verify line breaks, kerning, masking/descender clipping and safe zones across aspect ratios.
11. **Motion needs variation in intensity**: alternate emphatic beats with composed/quiet beats. Do not make every line as animated as the headline.
12. **Typography motion should be deterministic** given scene metadata and seed. Explain which rule selected an effect, to allow creative overrides.

## Animation vocabulary (choose based on intent)

| Family | Motion mechanism | Good use | Watch out for |
|---|---|---|---|
| Masked line reveal | Baseline-aligned lines rise through an invisible clip | Clear opening statement | Repeating on every scene |
| Per-letter convergence | Letter spacing and positions converge smoothly | Unity, precision, assembling an idea | Uneven glyph spacing, jitter |
| Scale + tracking transition | Whole word changes scale while tracking rebalances | Big claim or number | Overzoom, text touching edges |
| Opposing phrase convergence | Two semantic parts meet at a visual anchor | Comparison, connection, consequence | Equal hierarchy for both phrases |
| Word substitution | One word makes room for another within measured bounds | Process, alternatives, evolution | Jumping baseline and inconsistent widths |
| Photo-text occlusion | Masked typography travels behind/in front of a subject | Editorial depth and storytelling | Poor subject mask and contrast |
| Typographic wipe | Word silhouette becomes a mask for incoming image | Scene progression/reveal | Flashy transition without meaning |
| Path typography | Text follows a controlled curve/perspective line | Spatial or journey narrative | Unreadable rotated letters |
| Modular stack | Short phrases settle into a coherent grid | Structured argument or instruction | Generic repeating cards |
| Counter and unit choreography | Values and units animate separately with readable states | Metrics and proof | Fake counts and meaningless motion |
| Hold-and-accent | Main text stays still while one meaningful term transforms | High-information scenes | Overemphasis |
| Shared-element type morph | Letter/word geometry continues into next scene | Connected sequence | Frame discontinuity |

The renderer must support or gracefully downgrade unavailable primitives. **Never silently claim a sophisticated animation when only a fade or simple slide was rendered.**

## Rotation as an editorial motion tool

**Use rotation of photographic frames, crops, typography groups and occasionally individual words to create a more dynamic, art-directed rhythm.** Rotation must have a visual or narrative purpose and must harmonize with the rest of the film; it is not a random preset.

### Recommended mechanics
- **Tilt-and-settle:** an image enters at a slight angle, translates and settles into a precise grid alignment. Preserve subject/framing and avoid overly elastic easing.
- **Editorial diagonal composition:** a photo may remain deliberately tilted during a beat while the main headline stays horizontal and readable. The diagonal should create a directional relationship with the subject or photographic edge.
- **Rotating type block:** a short, large headline rotates as one group around an intentional pivot while entering or exiting; use an upright hold for reading.
- **Counter-rotation:** a moving or rotating photo and a headline can rotate in opposite directions with different timing so the overall composition balances. Do not create mirrored motion mechanically.
- **Rotation-to-layout transition:** a tilted crop straightens and expands into the next scene or becomes a new image mask, preserving continuity of its corners and pivot.
- **Controlled character rotation:** rotate an individual letter only if it reinforces a word's meaning or a specific choreography; never rotate every character merely for variation.
- **Depth-motivated perspective:** subtle rotations and parallax can suggest a card moving in 2.5D, but avoid fake 3D spinning cards with no depth/lighting consistency.

### Default art-direction ranges (suggestions, not hard limits)
- For ordinary editorial photo tilts, explore roughly 2–8 degrees. Larger angles need a clear reason and enough overscan.
- For headline groups, explore approximately 2–6 degrees during motion, then return to 0 degrees for longer text or information-heavy scenes.
- Bold one- or two-word display statements can use stronger rotation if the text remains legible and the move fits the audio/narrative.
- Alternate rotational accents with stable, precisely aligned scenes. **Do not rotate every scene** or repeat the same left-right tilt pattern.

### Geometry and rendering requirements
- Pick pivot deliberately: visual subject, meaningful word center, compositional corner or shared transition anchor; default center should not be assumed optimal.
- Compute rotated bounds at all animation extrema, including easing overshoot. Add image overscan before rotation so black/transparent corners never enter the viewport accidentally.
- Preserve text baseline spacing, glyph visibility and safe-zone clearance during motion; do not clip rotated ascenders/descenders with rectangular masks.
- Use appropriate spatially coherent motion blur where supported; the absence of motion blur must not be disguised as simulated camera realism.
- Keep text hierarchy readable in the hold frame and ensure motion does not obscure photo focal subjects.
- Coordinate translation, scale and rotation as a single trajectory with a clear visual mass. Never animate each property with unrelated easing curves.
- Do not use constant spins, frequent 180/360-degree text rotations, excessive oscillation, arbitrary bouncing, or tilted everything.
- For every rotation plan, store `pivot`, `angle_curve`, `overscan`, `reason` and `settle_angle` in the motion plan; verify actual rendered output supports these features.

### Variation planning
Count `rotating_group`, `frame_tilt`, `counter_rotation` and `rotation_to_layout` as related but distinct mechanisms **only when their choreography and compositional effect really differ**. Rotating the same card left instead of right does not count as diversity.

In a typical 4–6-scene reel, consider introducing rotation in one or two strategically chosen beats rather than all scenes. This is a discretionary creative starting point, not a quota.

### Acceptance checks
Review entry, maximum angle, readable hold and transition frames; assert no accidental clipping, no unsafe text placement, no unexpected matte corners and no conflicting simultaneous movement. A rotated result should look intentional when paused and coherent when played with sound.

## Selection algorithm: director-level criteria

For each scene, derive:
- semantic purpose, key phrase and message intensity;
- composition mode, word lengths, number of lines, focal image/subject;
- preceding/following animation family, visual density and motion direction;
- audio timing (speech emphasis, beat, pause);
- available animation capabilities and output aspect ratio.

Generate 3 candidate animation plans when possible. Score:
- semantic fit (30%);
- legibility and text geometry (25%);
- continuity with adjacent scenes (20%);
- mechanical diversity across a 3–5 scene window (15%);
- restraint and production feasibility (10%).

Treat these percentages as **starting assumptions subject to review**. Reject plans with clipping, insufficient reading time, poor contrast or motion-sickness/flash risk. If two candidates are equivalent, prefer the simpler.

**Diversity accounting**: track mechanism families rather than arbitrary effect names. A bottom-up word rise and a left-to-right word rise may count as a single `masked_reveal` family; animated tracking and character convergence count as `letter_geometry`. A variant is not considered novel just because color, easing speed or entrance direction differs.

## Shared timing rules

- Group text by meaning: word, phrase, sentence and supporting metadata; do not blindly stagger every glyph.
- Use a fast, clean arrival for the key idea, followed by a stable reading interval.
- Allow purposeful asymmetry: hero word may move earlier or more strongly than secondary text.
- Align important motion accents to the narration/music when available; a musical beat is not compulsory for every move.
- Exit should prepare the next scene; prefer continuity of direction, object identity or spatial anchor over unrelated wipes.
- Keep easing families consistent; select alternative velocity curves for different masses without random bounces.

## Suggested 4-scene progression (example, not a fixed template)

1. **WORDS MOVE** — masked two-line rise, compact stagger, full quiet hold.
2. **EXPLORE** — bold whole-word scale plus decreasing tracking, with camera/photo secondary.
3. **MAKE SPACE MATTER** — opposing phrase convergence and a meaningful accent on `SPACE`.
4. **COMPOSE / ANIMATE / REFINE** — measured word replacement anchored to a photo or visual grid.

In the *next* video, pick a different combination where it fits. Do not turn this example into four mandatory presets.

## Production QA checklist

For each scene record:
- `typography_family`, `semantic_reason`, `shared_motion_tokens`;
- entrance and hold duration, exit, easing profile and per-layer schedule;
- real glyph bounds and mask bounds over sampled frames;
- conflicts with subject, icons and platform safe zones;
- consecutive-family repetition and rolling diversity metrics;
- any creative override and its justification.

Render contact sheets at entrance, peak motion and settle. Review both isolated scenes and scene-to-scene rhythm, with sound and without sound. Automated checks should flag repeated families, but **do not reject deliberate repetition** (e.g. a rhythmic three-part sequence).

## Integration priorities

P0. Add scene metadata `typography_family`, `animation_intent` and optional `allow_repeat_reason` with defaults that preserve existing manifests.
P1. Implement a sequence-level diversity auditor that reports adjacent-family repetition, four-scene monotony and unsupported motion requests.
P2. Add letter geometry, tracking, semantic word replacements and subject-aware text masks with accurate glyph measurement.
P3. Build 3 candidate plans and choose with semantic, geometry, continuity and diversity scoring.
P4. Test with real photo-based reels and human art-direction review before promoting to default.

**Definition of done**: diverse motion is visible in actual exports, not just declared in a manifest; differences are semantic, readable and brand-coherent.
