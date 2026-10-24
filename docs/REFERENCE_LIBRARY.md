# Reels Maker — Professional Reference Library v1

**Date:** 2026-10-24. **Purpose:** reduce template-like, incoherent and low-quality AI-generated motion by making authored references and rejection rules part of actual creative QA.

This complements, rather than replaces, `docs/REFERENCE_BOARD.md` (18 external studio case studies), `docs/MOTION_DESIGN_SYSTEM.md`, `docs/DATA_MOTION_DESIGN.md`, `docs/ICON_LIBRARIES.md`, `docs/REVIEW_RUBRIC.md`, `docs/VISUAL_QA.md`, and the current `docs/MASTER_PLAN.md`. Those pre-existing docs are the full craft/backlog context; this file describes the *operational, machine-readable* layer.

## What is actually implemented

- **Single source of truth:** `src/reels_maker/creative/reference_data/library.json` includes sources, 14 traceable principles, 10 anti-patterns, five reusable editorial recipes and rule thresholds. All records are plain text and version-controlled.
- **Reader:** `reels_maker.creative.reference_library.load_reference_library()` validates citation IDs and gives a defensive copy. It works with editable installations and packaged wheels via `importlib.resources`.
- **Creative direction:** `reference_guidance(spec)` matches a recipe to Creative Spec v1 and emits the entire principle/anti-pattern list and reference links for an authoring agent.
- **Active QA:** `audit_reference_quality(spec)` flags deterministic warning patterns. `audit_creative_spec` uses it, so the existing `creative-qa` workflow receives issues with `reference_rules` and suggestions.
- **No imaginary aesthetic model:** The module *does not watch videos*, train on source works or claim human-like visual taste. Quality warnings are preflight heuristics; actual render/audio and independent editorial review are still mandatory.

## How an agent should use the library

1. **Intake:** Define a clear audience, one promise, factual evidence, brand, media rights and destination format. Check `brands/<slug>/BRAND.md`, the approved media catalog, and review-source provenance.
2. **Concept selection:** Read the library before constructing a Creative Spec. Match an editorial recipe and write a concise creative direction: subject, message, motif, visual treatment, pacing and proof beat.
3. **Shot design:** Every scene needs one information goal, an identifiable visual focal point, a semantic motion trigger, readable hold, and only a limited number of layers.
4. **Preflight:** Query reference QA *and* run existing `creative-qa`. Fix errors; explain or revise warnings. In strict mode warnings can block delivery.
5. **Visual validation:** Render storyboard/motion strips and final MP4. Test actual playback at phone size with audio, real overlay safe zones, subtitle durations, data values, photosensitivity, and asset rights. Record human rubric scores and final file hash before declaring success.
6. **Feedback loop:** Record rejected outputs as anonymized symptoms + fix + human-reviewed evidence. Do not reward a clip because an algorithm scores its own output highly.

```bash
# List machine-readable craft patterns and source URLs:
python -m reels_maker.creative.reference_library

# Return a matched professional recipe and full anti-pattern policy:
python -m reels_maker.creative.reference_library --spec examples/creative-engine-editorial-demo.json

# Apply editorial warning/error heuristics before / in addition to render QA:
python -m reels_maker.creative.reference_library --spec examples/creative-engine-editorial-demo.json --audit

# The project's normal creative-qa command also imports these findings.
```

## Reference families and transferable lessons

| Family | Primary references | Reusable mechanism | What NOT to copy |
|---|---|---|---|
| Semantic kinetic type | [Ordinary Folk — Gemini](https://ordinaryfolk.co/project/gemini) | Word emphasis tied to meaning; staggered word geometry; purposeful holds | Their exact frames, scripts or timing |
| Coherent CG/world-building | [BUCK — Get an Airbnb](https://buck.co/work/get-an-airbnb) | One distinctive world reused consistently; intentional transitions | Character models, visuals and designs |
| Live-action + graphics | [State — Dell](https://statedesign.tv/work/dell-all-the-right-moves) | Graphic motion anchored to real-world camera movement | Client material/shot recreation |
| Consistent campaign system | [Giant Ant — Slack](https://giantant.ca/slack-brand-campaign) | Repeat brand principles, not identical scene templates | Brand elements, fonts and palette |
| Product hero composition | [ManvsMachine — iMac Pro](https://manvsmachine.co/work/imac-pro) | Precise axial composition, clean stage, material-led lighting | Product likeness or copyrighted footage |
| Readable data stories | [Datawrapper bar chart guidance](https://www.datawrapper.de/academy/customizing-your-bar-chart) | Direct labels, sorted bars, useful annotations and sources | Layout that crops chart labels on mobile |
| Timed, functional motion | [Apple Motion HIG](https://developer.apple.com/design/human-interface-guidelines/motion), [Material easing](https://m1.material.io/motion/duration-easing.html) | Motion as signal, non-random easing and distance-aware timing | UI durations treated as hard limits for film editing |
| Platform-safe short video | [Meta Reels](https://www.facebook.com/business/ads/facebook-instagram-reels-ads), [IAB Polska](https://www.iab.org.pl/wp-content/uploads/2024/05/Short_Social_Video_IAB_Polska_052024.pdf) | 9:16 master, responsive safe zones, audio + captions | Fixed safe-zone pixels assumed valid for every platform/date |

**Source confidence:** Showcase links are *craft-level* study references carried over from the existing verified `REFERENCE_BOARD.md`; the new catalog has **no independently validated per-shot timestamps**. Do not infer exact frame timings from written summaries. Do not add external MP4s, music, thumbnails or client materials to the repository without a separate rights gate. See `AGENTS.md` for repository visibility constraints.

## Original, implementable motion sequences (not transcriptions of commercial reels)

These are **proposed original shot prescriptions**. Times are planning ranges, not observations from linked third-party clips.

### Example A — 15–18s B2B case-study proof reel (R01)

| Time | Meaning | Graphic grammar | Negative constraint |
|---|---|---|---|
| 0–2 s | Show a real installation, name one outcome | Clean real close-up + one large headline; quick semantic mask rise | No floating icons over unrelated stock |
| 2–5 s | Explain what was delivered | Cut to wider shot, tracked subtitle at safe margin | No paragraph or aggressive zoom |
| 5–10 s | Prove the result | Real footage + accurately sourced counter/chart overlay | No fabricated values or changing chart scales |
| 10–14 s | Add relevant context | One editorial lower-third/technical detail | No repeated template title card |
| 14–18 s | Convert | Stable brand CTA, clear contact destination | No flash, glow or needless bounce |

### Example B — 10–12s semantic type explainer (R02)

- **0–1.5s — question:** One typographic hero occupying a clear focal plane.
- **1.5–4s — concept:** Show two short terms entering with different **semantic** motions, not random presets.
- **4–8s — evidence:** Hold the actual metric or process illustration long enough to read, with source context.
- **8–12s — resolution:** Shared axis transformation into one clear branded takeaway; clean exit.
- Reject random letter explosions, the same pop animation for all text, pseudo-3D effects on every word, full-screen dynamic microcopy.

### Example C — 12–16s data-rich reel (R03)

- **0–2s:** State the comparison or question, period and unit.
- **2–6s:** Reveal chart scale and categories *before* animating marks; show honest baseline and axes.
- **6–11s:** Use stable entity IDs and preserve actual values through sorting, row-to-bar or chart morph; highlight the one finding.
- **11–14s:** Display settled values and a single sourced interpretation.
- **14–16s:** Optional CTA, still frame for readability. Human verifies screenshot of start/middle/end and full source data.
- Reject fake percentages, invented count-ups, truncating axes without explanation, unlabeled series and dense ten-column tables in 9:16.

### Example D — portfolio montage with beat-based cuts (R04)

- Wide / detail / human-scale / result shots, sourced from *clean* media.
- Transition only on an audiovisual event, motivated subject match or strong editorial contrast; hard cut is normally enough.
- Camera shutter FX only for a photographed moment, with varied cuts instead of a uniform slideshow.
- No auto-overlays on finished, pre-branded stock or client promos.

### Example E — product/technical 3D hero (R05)

- Product silhouette -> material detail -> mechanically accurate feature -> one proof moment.
- Light direction, texture response, shadows, perspective and occlusion must be internally coherent.
- 3D is only justified when it shows a real feature better than footage; do not use made-up geometry as technical documentation.

## Typography, animations, icons and data requirements

**Kinetic typography:** Use a coherent role hierarchy (kicker/headline/support), proper Polish characters, consistent leading/letter spacing, and deliberate focal-word scale contrast. Suggested entrance families: mask reveal, tracking-in, directional shared-axis, opacity/position stagger and morph of a common object. Entrance must have settle time; exit is usually shorter and simpler. Preserve an intentionally readable hold for the full phrase.

**Motion mechanics:** Avoid many simultaneous unrelated animated properties. Use causal triggering, clear trajectories and physically coherent easing. Timing is content-dependent, not a universal 200–300ms rule borrowed from UI microinteractions. Check overshoot geometry throughout the actual eased timeline; render preview strips before accepting the transition.

**Icons/SVG:** Pinned packs already supported: Lucide, Heroicons, Tabler, Phosphor and Material Symbols; see `docs/ICON_LIBRARIES.md` for exact pin/license details. Pick a semantic icon by concept, not randomly. Do not mix stroke widths/fill conventions across a sequence. Normalize bounding box and optical size; do not scrape logos or brand trademarks from SVG repositories.

**Tables/charts:** Emphasize semantic difference with bars, lines, area, waterfall, diverging bars, heatmaps, funnels, scatter, ranking, table sort/highlight and number transitions only when appropriate for the data. All animation phases must preserve identities, scale meaning and factual final values. Before rendering, link to source data, date, unit, period, denominator, missing values, transformations and accuracy; Creative Spec v1 has no provenance field, so `reference_chart_source_review` remains a documented review warning.

**Audio:** Cut, reveal and impact need a designed sound relationship. No gratuitous whoosh, click or shutter for every movement. Verify real voice onset and ducking in the final encoded deliverable.

**Safety:** Avoid aggressive flicker. W3C [WCAG 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html) is the external reference for dangerous flash thresholds; a JSON-only lint does **not** establish that the encoded MP4 complies.

## Operational anti-slop gate

The new automated preflight recognizes: `reference_unfinished_placeholder` (**error**), `reference_dense_subtitle`, `reference_flat_rhythm`, `reference_direction_missing`, `reference_recycled_headline`, `reference_generic_copy`, `reference_icon_family_mix`, `reference_asset_overuse`, `reference_chart_source_review` (**warnings**). Every code contains a suggestion and linked principle/anti-pattern IDs.

**This is not a numeric aesthetic score.** Deterministic detection can find some recurring mistakes, but cannot establish good storytelling, visual originality, polished animation, photography quality or emotional appeal. Human review uses `docs/REVIEW_RUBRIC.md` (0–4 per dimension); any 0/1 means reject, flagship requires 3+ in every dimension. Do not silently approve a poor visual solely because lint is clean.

## How to curate new references

1. Check source ownership, legal accessibility, working URL and credits; record `id`, title and actual original source.
2. If a human has **watched** a reference, capture independently verified timecodes with notes on semantic intent, spatial grouping, transitions, motion curve, durations, audio and negative lessons. If not viewed, timecode remains empty.
3. Extract **abstract, reusable** principles and add one operational recipe or negative example. No screenshots/videos from other brands are required.
4. Add a regression test demonstrating a previously rejected failure mode; avoid brittle overfitting to a single project or brand.
5. Require a human creative pass on actual phone and headphones after applying the change; track its acceptance status, not guessed quality percentages.
6. Periodically re-verify links and platform specs (which change). Cite dates; keep `library.json` version history for reproducibility.

## Definition of done for professional delivery

A source-verified narrative, legal/clean media, matched visual grammar, strong type hierarchy, purposeful motion, data fidelity, correct platform framing, mixed audio, no severe render-QA issues, human rubric approval, and a verified final MP4. **No source reference, model score or test suite may bypass this gate.**
