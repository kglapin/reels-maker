# Editorial typography: key words, pacing and restrained entrances

Use the headline `runs` JSON structure to emphasize a few meaningful words
without giving every word a different treatment. Mix at most two sizes in a
short headline, such as `0.8` for supporting words and `1.3` for the key
phrase. Apply the brand accent only to the decisive word, not to entire
paragraphs. Use explicit `break_before` to curate headline composition.

**Opt-in entrance styles:**
- `fade_stagger`: understated opacity entrance; useful for informational clips.
- `rise_soft`: gentle vertical appearance with ease-out; good for headlines.
- `slide_left`/`slide_right`: use only when motivated by screen direction.
- `editorial_reveal`: progressive presentation of the headline, kicker and CTA.

The same brand can have different typography treatments; brand.json only holds
identity, not animation styling. High-quality typography should be evaluated on
actual rendered frames, particularly accent contrast and safe areas. Use two
strong type hierarchies at most per composition. The intended hierarchy is
**video content -> hero word -> supporting text -> branding**.

Example: `brands/asta-energy/projects/asta-typography-editorial-demo.json`.
Test with the real ASTA media before using it as a public campaign asset.

## Precise mixed-size headline alignment

Styled text runs are aligned on a shared **font baseline**, not the top edges
of each text bitmap. The headline engine measures actual font ascent, descent
and word advances, then wraps complete words into line boxes. A 130% hero
word beside a 70% supporting word no longer appears to float vertically.

Supporting title/body sizes were increased so condensed reels retain
a practical text hierarchy on phone-size playback. This is an **editorial
default**, not a fixed brandbook resolution; users still select arbitrary
portrait, landscape and square formats. Oversized/long words fail the safe
text-area checks rather than being silently shrunk.

Optional per-scene `title.backdrop` choices: `soft` (default, gentle dark
gradient), `strong` (more contrast on detailed footage), `none` (only after
checking text contrast against the actual frames). No stock glowing panels,
colored glass, perpetual zoom or automated flashy masks.
