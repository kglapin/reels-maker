# Reels Maker — agent-friendly CLI

The same command-line entrypoint works from a human terminal, ChatGPT, Pi,
OpenCode, shell scripts and CI. It is **noninteractive** and prints JSON on
successful completion or when \`--json\` is supplied (including errors).

## Setup

Requirements: Python 3.11+, FFmpeg and FFprobe on PATH. Install with
\`python -m pip install -e .\` in a local repository checkout.

Commands:

\`\`\`sh
reels-maker validate projects/asta-montage.json --json
reels-maker render projects/asta-montage.json --json
reels-maker render projects/asta-montage.json --output output/alternative.mp4 --json
reels-maker inspect output/asta-montage.mp4 --json
\`\`\`

Example success response:

\`\`\`json
{
  "ok": true,
  "output": "/absolute/path/output/asta-montage.mp4",
  "duration_requested": 30.0,
  "scenes_total": 15,
  "scenes_encoded": 0,
  "cache_hits": 15
}
\`\`\`

Full render output also includes actual duration, size, format and resolution.
Exit code 0 signals success; exit code 2 signals validation or rendering failure.
The error payload includes a stable top-level \`ok: false\` and a typed message.
Always use \`--json\` from harnesses, parse the exit code, and only use files
whose \`ok\` value is true.

## Manifest contract

Configuration uses JSON with keys: \`name\`, \`video\`, \`scenes\`,
optional \`music\`, optional \`branding\` and \`output\`.

- A scene has \`file\`, \`start\` (seconds, default zero), \`duration\`
  (seconds), \`framing\` (\`crop\` or \`pad\`) and optional \`title\`.
- \`title\` can include \`kicker\`, \`headline\` and \`body\`.
- \`music\` can include \`file\`, \`start\`, \`volume\` and \`fade_out\`.
- \`branding\` can include \`logo\` (path relative to asset root),
  \`accent\` (#RRGGBB), \`font_regular\`, \`font_bold\` (system font paths).
- Video defaults: width=1080, height=1920, fps=25.
- File paths are relative to the root (the repository checkout by default).
  Use \`--root /path/to/assets\` for another location.
- Output defaults to \`output/video.mp4\` and can be overridden by \`--output\`.
- Cache defaults to \`.cache/reels-maker\`; bypass with \`--no-cache\`.

## Performance

Each segment is encoded with FFmpeg once, then cached using source path,
size, modification timestamp, scene configuration and branding settings.
Repeated renders reuse unchanged segments and concatenate them with stream
copy. Only final music multiplexing is repeated. Outputs are atomically
replaced after successful verification, protecting earlier renders.

The cache is *local*, not stored in Git. File metadata cache keys favor speed;
if input content is deliberately replaced while preserving size and mtime,
remove \`.cache/reels-maker\` or use \`--no-cache\`.

Rendering supports concurrent processes via isolated temporary workspaces.
For collaboration use a shared asset store or an explicit \`--root\`;
GitHub is the source for code, not a low-latency video-render filesystem.

## Agent usage

Tell Pi / OpenCode / ChatGPT to:
1. Write or edit one manifest JSON using known asset paths.
2. Call \`reels-maker validate <manifest> --json\`.
3. Fix reported errors, then call \`reels-maker render <manifest> --json\`.
4. Present \`output\` from the successful response. Do not claim success merely
   because an FFmpeg process started.

The CLI does not require an interactive shell, elevated credentials, access to
a model API or any persistent network connection.

Parallel scene encoding: `--jobs 1..8` (default: 2). `doctor --json` checks FFmpeg. `validate --syntax-only --json` verifies manifests without requiring media.

## Find source files before authoring a manifest

```sh
reels-maker catalog --root . --json
reels-maker catalog --root . --probe --limit 100 --json
```

The default catalog scans paths and file sizes only (no FFprobe). It excludes render outputs and working/cache folders. `available: false` identifies an unhydrated Git LFS pointer, which must be downloaded before rendering.

## Declarative legacy baselines

- `projects/asta-vamos-beat.json`: 22 cuts preserving the original beat times.
- `projects/asta-subsidy-external.json`: 9 externally sourced scenes, Polish overlays and supplied Rush audio.
- `projects/asta-rush-demo.json`: short branded integration reference.

These are configuration-driven **baselines**, not frame-identical exports of the original
scripts. Legacy green-flash transition overlays, exact source in-points, and original
compositing treatments are pending migration. The subsidy edit requires Git LFS
footage (`git lfs pull`) and a fresh check of programme claims and licences.
