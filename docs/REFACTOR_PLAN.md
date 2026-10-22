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
- [x] Mixed-size highlighted words and curated directional typography entrance presets.
- [x] Explicit narration-time / beat cue scheduling for each semantic text run, deterministic FPS quantization and preflight checks.
- [x] Optional independent narration soundtrack with deterministic offset, silence padding, music ducking and peak limiting.
- [x] Frame-accurate cue-sheet exporter with global timeline and xfade overlap warnings for human narration spotting.
- [x] Editor-verified audio word marker audit with explicit frame tolerances, source checks and strict-quality drift warnings.
- [x] Read-only FFmpeg/EBU R128 loudness and AAC true-peak QC, with warnings but no automatic mastering.
- [ ] Migrate historical film-burn/green-flash assets as an optional separate layer, if approved.
- [x] Machine-readable editorial quality warnings for reading speed, over-emphasis and transition density, with CLI strict mode.
- [x] Real-MP4 storyboard generation for human shot/crop/text inspection.
- [x] Optional entry/settled/exit motion-strip review from actual decoded frames.
- [x] Strict render mode and updated Pi/OpenCode/ChatGPT publishing workflow.
- [x] Post-encode MP4 verification (exact frame count, FPS, codec, audio streams) before atomic publication.
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
