# Reels Maker — single-PR refactor plan

All work for this refactor is committed to `refactor/modular-render-engine`.
The `main` branch must not be changed before the complete draft PR is reviewed.

## Ordered milestones

- [x] A. Introduce Python package, versioned dependencies, portable paths and Unicode/LFS safety checks.
- [ ] B. Build a shared FFmpeg render pipeline, validation and quality inspection.
- [ ] C. Add JSON manifests for legacy Rush, Vamos, ASTA subsidy videos.
- [ ] D. Convert legacy entrypoints to thin wrappers while preserving their names.
- [ ] E. Add CLI, documentation, regression tests and continuous integration.
- [ ] F. Review media licensing, binary asset storage and deterministic production outputs.

## Compatibility criteria

1. No fixed `/Users/...`, `/System/Library/...`, or shared `/tmp` paths.
2. Projects can be rendered from anywhere after `pip install -e .` with FFmpeg installed.
3. Git LFS pointers are detected with an actionable error before rendering.
4. Renders are 9:16 H.264 MP4 with AAC audio if a music track is configured.
5. The pull request stays in draft until reproducible render validation is documented.

## Existing Git data

Retain pre-existing renders and intermediate files in the refactor PR for safety.
Do not attempt to purge past Git history as part of this refactor.
