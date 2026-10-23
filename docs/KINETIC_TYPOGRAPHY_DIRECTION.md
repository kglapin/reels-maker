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
9. **Avoid AI-slop defaults**: no side rails, arbitrary underlines, bouncing every word, rotating individual letters for novelty, glow/gradient clutter, meaningless kinetic separators or every-word colored emphasis.
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
