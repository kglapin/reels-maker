# Reels Maker — single-PR refactor plan

All refactor work is committed only to `refactor/modular-render-engine`.
The `main` branch must not be changed before the complete draft PR is reviewed.

## Architecture principle

Optimize for fast, deterministic renders callable by ChatGPT, Pi, OpenCode and
shell scripts. Module count is *not* a metric. Prefer separate responsibilities
where useful, but do not duplicate FFmpeg pipelines or build unneeded wrappers.

## Ordered milestones

- [x] A. Python package, versioned dependencies, portable paths, Unicode/LFS checks.
- [x] B. Shared FFmpeg renderer with cached scene encodes and stream-copy assembly.
- [x] C. Noninteractive JSON CLI: validate, render, inspect.
- [x] D. JSON example for an ASTA music montage.
- [~] E. Migrate legacy generators: declarative Rush, Vamos and subsidy baselines now exist; their legacy transition effects still require parity work.
- [ ] F. Add effects, reusable brand presets and safety-zone configurations.
- [ ] G. Review media licensing, binary storage and deterministic production outputs.
- [ ] H. Validate real source media in a full-size production export.

## Compatibility criteria

1. No fixed `/Users/...`, `/System/Library/...` or shared `/tmp` paths
   in active rendering paths.
2. Projects render after `pip install -e .` with FFmpeg available.
3. Git LFS pointers fail with an actionable error before rendering.
4. Renders are H.264 MP4 with AAC audio when music is configured.
5. Subsequent identical renders reuse the cached scene videos.
6. Cut boundaries are quantized cumulatively to avoid beat drift on long montages.
7. Failure does not overwrite the last successful final output.
8. The pull request stays draft until source-media validation is complete.

## Existing Git data

Retain pre-existing renders and intermediate files in the PR for safety.
Do not rewrite Git history as part of refactoring. Intermediate output
directories are ignored for *future* changes; previously tracked binaries
remain present until a separate, approved media migration.
