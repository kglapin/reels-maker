# Multi-brand directory

Each brand owns one `brand.json` with technical defaults, a `BRAND.md` for
creative instructions, reusable assets under `assets/`, media under `media/`,
and projects under `projects/`.

A project sets `"brand": "<slug>"` and uses paths **relative to its brand**
(e.g. `"file": "media/footage/clip.mp4"`). The renderer resolves and validates
these names to `brands/<slug>/...` before passing them into FFmpeg.

Brand manifests inherit defaults such as `branding.accent` and logo, while
project-level settings can intentionally override them. No brand-specific
logic or directories are embedded inside the FFmpeg renderer.

## Separation of concerns

`brand.json` describes identity only (colors, typography, logo, creative rules).
Do not store width, height, aspect ratio, FPS or pixel safe areas in it.
Each video project owns `video.width`, `video.height`, `video.fps` and
optional `branding.safe_areas`. This permits multiple social, web, landscape,
square and portrait formats to share the same brandbook and media library.
