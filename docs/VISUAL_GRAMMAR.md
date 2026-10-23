# ASTA Energy — Visual Grammar (ART-03)

## Core Principles
Based on brand.json and BRAND.md guidelines, the ASTA visual grammar prioritizes
comprehension and professionalism over spectacle. Effects are secondary to clear
information hierarchy.

### 1. Color Restraint
- **Primary color: `#47A013`** — use green intentionally, not as heavy gradients
- **Background: `#FFFFFF`** — white base; scrims only when needed for contrast
- **Text: `#FFFFFF`** — white on bright footage, `#14221A` (neutral) on dark footage
- **Accent usage** — `#47A013` only for emphasized runs, not for general text
- **Never** use green as a dominant background or gradient fill

### 2. Typography Hierarchy
- **Preferred typeface: Open Sans** (fallback: DejaVu Sans)
- **Sequence**: optional kicker → headline → supporting body → footer
- **Headline** — visually dominant; must be readable within first second
- **Body copy** — supporting detail; larger scale than microcopy; shared baseline
- **Kicker** — optional very-short pre-heading; if used, scale < headline
- **Footer** — optional CTA or secondary info; smallest scale

### 3. Authentic Logo Usage
- **Logo file**: `assets/logo.png` for video overlays; `assets/logo.svg` is the original
- **Clearspace**: minimum margin around logo equal to logo height
- **Background**: `#14221A` (neutral) for logo preview; white logo on dark stays readable
- **No duplicates** — do not overlay new logo on top of already-branded footage

### 4. Predictable Information Order
Per-scene text layout follows this order:
1. **Kicker** (optional, 1-2 words, scaled down)
2. **Headline** (rich text runs with mixed emphasis/accent color)
3. **Body** (supporting detail, longer copy)
4. **Footer** (optional CTA or secondary info)

### 5. Motion Restraint
- **Style**: minimal, purposeful; no automatic effects
- **Entrance**: ease-out on entrance, small distance (16-28 px at 1080px reference width)
- **Stagger**: 2-3 frames between elements at 25-30 FPS is typically enough
- **No**: bounce, shake, unnecessary FX, spinning titles, random zooms
- **Transitions**: tied to story or music; cut is default; dissolve/motion_wipe opt-in

### 6. Rejection Examples (ART-10)
- Spinning titles
- Stock light leaks on every cut
- Random zooms
- Unreadable microcopy
- Aggressive glow effects
- Crowded compositions without hierarchy

### 7. Minimum Hold/Read Times (ART-11)
- Headline: minimum 0.55s settled frame hold after entrance completes
- Body: additional read time proportional to character count (~19 chars/s reading speed)
- Total scene duration must allow readable hold after all entrances complete

### 8. Format Independence
- Never derive typography exclusively from width or assume 9:16
- Relative typographic scale uses the *shorter* video dimension
- Explicit project safe areas use exact output pixels; unset margins follow output ratios
