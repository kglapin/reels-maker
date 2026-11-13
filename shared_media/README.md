# Shared app media

Files in this directory can be referenced by any brand in a project manifest
with a `shared://` path, for example `shared://audio/polaroid-shutter-click.mp3`.
The Studio asset resolver keeps those paths inside `shared_media/`.

The Polaroid shutter sound was supplied by the repository owner. Verify any
applicable usage rights before publishing media that contains it.

## Mixkit sound effects (downloaded 2026-11-12)

The `ui-*.wav` samples are unmodified downloads from Mixkit
(https://mixkit.co/free-sound-effects/), used under the Mixkit License, which
permits commercial use without attribution. Source item pages:

- `ui-pop.wav` — "Dry pop up notification alert", item 2356
  (https://mixkit.co/free-sound-effects/pop/)
- `ui-tick.wav` — "Modern click box check", item 1120
  (https://mixkit.co/free-sound-effects/click/)
- `ui-whoosh.wav` — "Cinematic whoosh fast transition", item 1492
  (https://mixkit.co/free-sound-effects/whoosh/)
- `ui-chime.wav` — "Crystal chime", item 3108
  (https://mixkit.co/free-sound-effects/chimes/)

Direct file URLs follow `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`.
The earlier self-synthesized `*-soft.wav` samples were removed at the owner's
request; new SFX must be downloaded from licensed libraries, not generated.
