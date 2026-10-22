# Editorial motion design — restrained, hierarchy-first

The primary goal is comprehension, not spectacle. Enter each element only if
there is a communicative reason. Treat FFmpeg `xfade` (shot transitions) and
`motion` (in-shot element animation) as independent timeline systems.

## Preferred patterns

1. **Cut as default:** every shot change is a cut unless its creative brief
   explicitly calls for a transition. Keep meaningful cuts locked to speech,
   action or music; do not randomly cycle through presets.
2. **Typography hierarchy:** sequence an optional kicker, then the headline,
   then supporting detail. Make the headline visually dominant. Let each
   element settle into a fully static, readable state.
3. **Modest stagger:** 2–3 frames between elements at 25–30 FPS is typically
   enough for an intentional cascade; adjust for the actual scene duration.
4. **Natural deceleration:** ease-out on entrance, small distance (roughly
   16–28 px at a 1080px reference width), opacity interpolation, no bouncing.
5. **Speech alignment:** synchronise text reveals to relevant narration rather
   than always beginning at shot start. Explicit timing parameters for spoken
   phrases are a future extension, not something to infer automatically.
6. **Avoid:** glitch and random shake, unsolicited film-burn or colored flashes,
   split-letter effects, spinning titles, stock zoom transitions, overshoot,
   and persistent motion that competes with information.

## Implemented

An opt-in `motion.preset = editorial_reveal` uses locally created separate
RGBA assets for the logo, kicker, accent, headline, body and footer. FFmpeg
composes cropped layers with staggered alpha fade and cubic ease-out y-offset.
`fade_stagger` removes translation. Static cards remain identical when motion
is unspecified. Per-scene duration limits prevent animation from overtaking the
message. Every shot is cacheable independently of shot assembly.

Reference principles:
- [Apple Motion](https://developer.apple.com/design/human-interface-guidelines/motion)
- [Material duration & easing](https://m1.material.io/motion/duration-easing.html)
- [Adobe After Effects — animating text](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html)
- [Morningstar Motion Design](https://design.tec7072a.eas.morningstar.com/foundations/motion)
- [Greenhouse Motion Language](https://brand.greenhouse.com/motion-language)

Do not interpret these sources as a frame-by-frame audit of any specific ad.
Creative parity requires comparing actual reference videos and exported frames.

## Editorial quality gate (automated, but not aesthetic certification)

`reels-maker validate <manifest> --syntax-only --strict-quality --json`
returns a machine-readable failure if conservative warnings are present.
The render API emits `quality.status`, `quality.warning_count` and
structured warnings for downstream agents. It checks text reading-time
budget (~19 characters/s), a settled frame hold, too many emphasized runs,
and excessive or repeated transition presets. It never automatically
rewrites the user's story or inserts effects.

**Passing these checks does not certify professional quality.** A real final
review still needs proxy playback on a phone, legible contrast against
footage, deliberate shot choice, narrated audio timing and licensed content.
