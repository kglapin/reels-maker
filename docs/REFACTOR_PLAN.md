# Single draft-PR refactor plan

Development branch: `refactor/modular-render-engine`. All changes belong
to one draft PR. Do not merge until regression acceptance and a manual review.

## Milestones

- [x] A. Package Python source and pin compatible dependency ranges.
- [x] B. Introduce portable paths, Unicode normalization and LFS checks.
- [x] C. Implement a reusable FFmpeg pipeline and isolated scratch work.
- [x] D. Add cached per-shot encodes and atomic final MP4 outputs.
- [x] E. Provide versioned JSON CLI for ChatGPT, Pi and OpenCode harnesses.
- [x] F. Add a sample manifest, basic tests and GitHub workflow.
- [ ] G. Port Rush/Vamos legacy visual effects and preserve beats/transitions.
- [ ] H. Convert legacy scripts into configuration-based compatibility commands.
- [ ] I. Compare audio/video outputs for migrated samples and optimize performance.
- [ ] J. Review licensed binaries, LFS fetches and final build documentation.

## Success criteria

- Cross-platform without absolute macOS paths in new engine.
- Render API/CLI independent of an interactive terminal.
- Exact JSON status and output path for each invocation.
- Hot-cache render does not re-encode unchanged shots.
- Concurrent jobs use separate temp directories and atomic cache writes.
- Archive scripts remain available until compatible replacements are verified.
- `main` remains unchanged until explicit approval of the complete PR.

## Deliberately excluded from the first working renderer

- Beat quantization and complex overlays from the historical montage tools.
- SFX / voiceover mixing and dynamic keyframed animations.
- Hardware-specific codec optimizations and distributed render workers.

These features must be added only when benchmarked against real use cases,
not as speculative extra abstraction.
