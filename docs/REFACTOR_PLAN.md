# Reels Maker — single-PR refactor tracker

All refactor work belongs to `refactor/modular-render-engine` and draft PR #1;
`main` must remain unchanged until final approval.

## Architecture milestones

- [x] Engine in `src/reels_maker/` with portable FFmpeg and CLI.
- [x] Independent brand folders with `brand.json`, `BRAND.md`, assets and media.
- [x] Brand-specific project manifests with inherited design defaults.
- [x] Outputs separated from sources: `renders/<brand>/`, local cache.
- [x] Legacy sources and historic intermediates moved without rewriting Git blobs.
- [x] FFmpeg scene cache, stream-copy assembly, frame-accurate montage cuts.
- [x] Agent/terminal documentation and synthetically generated integration tests.
- [x] Brand-scoped synthetic render tests, including brand change cache invalidation.
- [x] Curated opt-in xfade presets, frame-accurate overlap, validation and synthetic tests.
- [x] Independent opt-in title/logo animation layers with stagger, easing, validation and FFmpeg test coverage.
- [ ] Migrate historical film-burn/green-flash assets as an optional separate layer, if approved.
- [ ] Verify representative production render from each existing project.
- [ ] Compare cold/warm performance and visual regressions for legacy footage.
- [ ] Validate third-party source licences, programme facts and publish rights.
- [ ] Review Git LFS and long-term large-media storage; avoid rewriting history.

## Storage and reproducibility

- `src/` contains shared engine code; never copy it per brand.
- `brands/<slug>/` contains brand JSON, Markdown guidance, input assets,
  footage/audio/effects and animation manifests.
- `renders/` contains the generated MP4s, ignored by Git; previously tracked
  reference exports remain under `renders/<slug>/archive/`.
- `archives/` stores old intermediate media for audit.
- `legacy/` stores old machine-specific scripts, not production entrypoints.
- `.cache/` stores disposable scene encodes; it is not stored in Git.

Historical media remain Git-tracked during this PR for traceability; physical
Git repository size will not decrease just by moving paths. A separate media
archive/storage migration can address history size safely.
