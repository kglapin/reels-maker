# Professional Typography System — Reels Maker (2026-10-24)

## Scope

This is the **operational reference and active quality gate** for typography in motion graphics and short social video. The authoritative machine-readable configuration is `src/reels_maker/design/typography_profiles.json`; its loader and validators live in `src/reels_maker/design/typography_policy.py`.

The new system **adds guidance and checks** to existing real-font typesetting, safe-polygon tests, geometric collision detection, text-ink checks and contrast/hold QA. It does not silently replace production fonts, alter the user's copy, or introduce a competing renderer. Passing the checks is not a professional art-direction certification.

## 1. Research: ready-made typography systems and templates

The following are external design systems with genuine published scales, applied here as **inspiration**, not copied brand identity:

1. [IBM Carbon: Type Sets](https://www.carbondesignsystem.com/building-blocks/foundations/typography/type-sets) — explicit style-role tokens and distinct *productive* vs *expressive* systems.
2. [IBM Design Language: Type Scale](https://www.ibm.com/design/language/typography/type-scale/) — a predefined hierarchical progression such as 12, 14, 16, 18, 20, 24, 28, 32, 36, 42, 48, 54, 60, 68, 76, 84, 92 px; type/line-height pairings.
3. [Material Design 3 Typography](https://developer.android.com/develop/ui/compose/designsystems/material3) — 15 baseline categories across display/headline/title/body/label. Example UI styles: displayLarge 57/64 sp, headlineLarge 32/40 sp, bodyLarge 16/24 sp. **These are UI values, not recommended pixel sizes for a rendered 1080p Reel.**
4. [GOV.UK Type Scale](https://design-system.service.gov.uk/styles/type-scale/) — responsive font/line-height pairs on a consistent vertical rhythm (e.g. 48/50, 36/40, 24/30, 19/25 on larger screens).
5. [U.S. Web Design System Typography](https://designsystem.digital.gov/components/typography/) — headings closer to related content than preceding content; short display text can have tighter leading; extended body benefits from greater leading and controlled line measure. 45–90 character lines apply to **long-form web reading**, not 1–3 line animated titles.
6. [Atlassian Applying Typography](https://atlassian.design/foundations/typography/applying-typography) — clear levels of dominance, short headings, deliberate weight/size contrast and reading-length control.
7. [GOV.UK Social Typography](https://brand.design-system.service.gov.uk/typography/social/) — explicitly illustrated correct vs incorrect tracking/leading in social assets.
8. [Material Design Metrics & Keylines](https://m1.material.io/layout/metrics-keylines.html) — 8-unit grid / 4-unit text baseline recommendations for UI, translated into proportionally scaled compositional tokens here.
9. [Adobe Premiere — Safe Zones](https://helpx.adobe.com/uk/premiere/desktop/get-started/source-and-program-monitor-adjustments/view-safe-zones-in-the-monitors.html) — type should remain inside verified format/placement-safe areas; old generic broadcast title margins are **not automatically sufficient** for app action rails.
10. [W3C WCAG 2.2 Text Spacing](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing) — **important caveat:** SC 1.4.12 checks whether adaptable HTML/CSS can survive user overrides of line spacing 1.5x, paragraph spacing 2x, tracking 0.12em and word spacing 0.16em. It does *not* mandate that these values be burned into every MP4 title.

## 2. Semantics before font sizes

### Semantic scale (design pixels at short side = 1080)

These are **Reels Maker editorial recommendations**, developed from the sources above. They are not platform-published minima.

| Role | Editorial/B2B | Dynamic advertising | Data/storytelling | Purpose |
|---|---:|---:|---:|---|
| Display | 150 | 174 | 132 | Hero statement, 1–2 lines |
| Hero | 122 | 146 | 108 | Key word, figure, product promise |
| Title | 82 | 92 | 72 | Main statement / section |
| Subtitle | 48 | 54 | 46 | One explanatory clause |
| Body | 38 | 42 | 40 | Readable short supporting explanation |
| Caption | 32 | 34 | 34 | Evidence label, attribution, descriptor |
| Kicker | 28 | 30 | 28 | Optional compact contextual label |
| Micro | 24 | 24 | 26 | Small information, never the main claim |

Each style additionally encodes **its own line-height, weight and expected maximum lines**. Retrieve the full table via `suggested_typography(...)` or inspect JSON. Higher type roles should dominate by **size and/or deliberate weight**, not by stacking decorative outlines, shadows and gradients.

### Line-height / leading

- Hero/display: approx. **1.03–1.10** for one or two lines.
- Main title: **1.10–1.12**.
- Subtitle: **1.22–1.24**.
- Body: **1.30–1.38** (long text often benefits from more).
- Caption/kicker: generally **1.24–1.34**.
- Multi-line leading **below 1.05** is a warning. Long text of 75+ characters spanning 3+ lines with leading below **1.27** is a warning.
- The correct line height depends on actual font metrics, language, number of lines and design intention; a single multiplier for every role is an anti-pattern.

### Tracking / letter spacing / case

- Start with the font's native kerning; adjust optical tracking sparingly.
- **Unusually tight (< -0.07em)** or wide **(> +0.16em)** tracked copy triggers a review warning.
- Do not attempt to create hierarchy with excessive tracking and all-caps paragraphs; uppercase is reserved for short high-impact phrases or labeled concepts.
- Keep Polish diacritics intact. Measure actual glyph ink (including ascenders and accents), not an approximate Latin-only bounding box.

### Space, alignment and grouping

- Use an **8-unit grid** for containers and **4-unit** text baseline increments as drafting aids at design short-side 1080; scale proportionally by shorter canvas side.
- Preferred text/element stack gaps at 1080 design width: **16, 24, 32, 48, 64, 96px**. Use smaller gaps within a conceptual group, larger gaps between distinct groups.
- A headline should be visually closer to the supporting subheading than to an unrelated preceding component.
- Consistent shared left or center axis; don't mix arbitrary alignments inside one two-line statement.
- Use `PLATFORM_PROFILES` and existing safe polygons rather than assuming the same pixel margins for Reels, TikTok, Shorts, 1:1 and 16:9.

### Geometry and formats

All guidance is anchored to **1080 px on the shorter side**. Resolution `360×640` scales recommendations to 1/3; `1080×1350` retains base sizes; `1920×1080` retains base sizes but must reflow layout in wide orientation. Font scales alone do not guarantee a usable layout: actual FreeType measurement and safe-zone geometry remain the final gate.

## 3. Ready-to-use video typography recipes

### A. Editorial claim + evidence (B2B)
- Small kicker (optional): contextual label / service, no competing shadow/glow.
- One principal statement in **title/hero** scale, usually 1–2 lines.
- Short supporting explanation in **subtitle** scale, separated by one system gap.
- Short factual source or figure in **caption** scale.
- **Reject:** four headings of similar size, broken word pairs, illegible source labels, arbitrary dense overlays.

### B. High-contrast kinetic headline
- Up to two intended levels of emphasis: one **hero word** and supporting **title**.
- Large word may be animated by meaning, but baseline/kerning must remain consistent when it settles.
- Sequential entrance **must preserve final readable hold**; do not introduce extra words faster than they can be read.
- **Reject:** long all-caps sentences, multiple unrelated font families and uncontrolled per-character size variation.

### C. Charts and dashboards
- Reading order: proposition → chart/title → axes/units/categories → value labels → source.
- Use **title + body/caption**, preserve units and real values, and keep exact tick/data labels visible in final-frame PNG QA.
- Prefer full-screen one-variable chart over ten-column table in portrait. Show time/period and data provenance.
- **Reject:** tiny axes, label overlap, numbers/units that detach during animation, unverifiable data.

### D. Captions and subtitles on footage
- Keep real footage visually unobstructed; text placed on a tested safe region with a contrast-preserving backing if necessary.
- Split long copy at phrase/syntax boundaries; limit line count and excessive tracking.
- Animate one semantic clause at a time rather than a full paragraph entering at once.
- Check color/exposure, audio-onset alignment and readability against **actual footage at phone size**.

## 4. Enforced anti-slop contract

### Preflight before render (Creative Spec)
`audit_creative_typography()` is included in the existing `audit_creative_spec()` / `creative-qa`. Flags an excessively long single focal headline and overlong uppercase headings. These are **warnings**; copy editing needs human judgement.

### On real rendered text (Studio `studio-qa`, full audit and scene candidate QA)
`audit_typography_blocks()` receives real `TextBlock` objects and catches:
- `typography_critical_size` — **error**: actual font raster size below a conservative format-aware absolute floor.
- `typography_small_text` — **warning**: below recommended size for that semantic role.
- `typography_too_many_lines` — **warning**: excessive wrapped lines.
- `typography_tight_leading` and `typography_long_copy_leading` — **warnings**: compressed line-height.
- `typography_extreme_tracking` — **warning**: unusual per-glyph spacing.
- `typography_weak_hierarchy` and `typography_subtitle_body_hierarchy` — **warnings**: competing text levels.

`audit_typography_tokens()` additionally flags non-monotonic type or spacing scales. The existing hard checks for truncation, collisions, contrast and UI-safe geometry continue independently.

Warnings in non-strict mode demand visual/editorial review; they are not auto-evidence of failure. Human reviewers may approve deliberate expressive exceptions after viewing actual frames. A new error means **do not deliver** until fixed; video should never be exported as approved solely because heuristic checks pass.

## 5. Code usage

```python
from reels_maker.design.typography_policy import (
    load_typography_profiles, suggested_typography,
    audit_creative_typography, audit_typography_blocks,
)

# A designer/agent reads actual presets before authoring shots.
preset = suggested_typography("editorial-premium", 1080, 1920)
print(preset["roles"]["hero"])      # includes size_px and line_height
print(preset["stack_gaps_px"])

# Native Creative Spec v1 copy can be audited before compilation:
copy_warnings = audit_creative_typography(creative_spec)

# Studio audit / storyboard quality checks automatically evaluate measured
# TextBlock objects after normal type fitting and line breaking.
```

The JSON policy is bundled into wheels and editable installs under `reels_maker.design` (no external runtime fetch). Regression tests include actual measured text blocks, line spacing, hierarchy, all-caps copy, scaled dimensions, source integrity, invalid token ordering, and integration into `creative-qa`.

## 6. Definition of done for typography in a finished Reel

Type roles follow a deliberate hierarchy; copy fits without truncation or meaningless downscaling; all characters, including Polish glyphs, are legible; actual frame geometry respects platform safe areas and contrast; text holds are long enough; sound and cuts align; subtitles and data labels remain readable on an actual phone; a human reviewer signs off against `docs/REVIEW_RUBRIC.md`.
