# Contract for Pi, OpenCode, ChatGPT and other terminal harnesses

This project is a **command-line rendering tool**, not an autonomous agent.
Treat it as a deterministic subprocess. Agents should only create/change
project manifests, invoke documented CLI commands and inspect their JSON response.

## Recommended loop

1. Create a small JSON project based on `projects/asta-rush-demo.json`.
2. Run `reels-maker validate <path> --syntax-only --json` for schema errors.
3. Run `reels-maker validate <path> --root <repo-root> --json` to inspect assets
   and prevent expensive failed renders.
4. Run `reels-maker render <path> --root <repo-root> --json`.
5. Read the successful JSON `output` field and inspect/preview the resulting MP4.
6. On failure, use stderr JSON `type` and `message` to revise the manifest.

## Machine interface

- No prompts, no TTY requirement, no background processes.
- Schema version: `1`, encoded as JSON on stdout after success.
- Exit status `0`: success; `2`: invalid config, missing input or render failure;
  `3`: missing CLI prerequisite on `doctor`.
- Output artifacts are absolute paths in render result JSON.
- Every render uses a new scratch directory, so parallel harness calls do not
  share or delete each other's working data.
- Scene cache uses content-addressed keys derived from source file metadata,
  effects, brand configuration and output settings. Files are published atomically.
- The engine makes no external network requests and does not require secrets.
- Existing material from this repository should not be uploaded to external
  APIs unless redistribution rights are confirmed.

## Performance guidance

- Reuse normalized shot cache when changing only audio or shot ordering.
- Independent shots encode concurrently with two FFmpeg workers by default.
  Set \`--jobs 1\` on memory-constrained runners or \`--jobs 4\` on stronger hosts.
  The number of workers is bounded to 1–8.
- Avoid `--no-cache` except while debugging.
- Prefer `crop` for vertical sources; `pad` for wider sources where losing
  the subject is unacceptable.
- Media duration and existence are checked before any encoding starts.
- No intermediate MP4 is committed into Git; artifacts remain in `output/`.
- Concurrent renders writing to **different** output files are supported.
  If multiple agents request the same output path, use distinct `--output` values.
- Current encoder is portable CPU H.264 (`libx264`). Adaptive hardware encoders,
  speech/SFX mixing and transition FX are future work, not present functionality.

## Example for shell-based agents

```sh
set -e
reels-maker validate projects/asta-rush-demo.json --root . --json
reels-maker render projects/asta-rush-demo.json --root . --json
```
