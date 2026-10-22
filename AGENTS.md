# Reels Maker — harness instructions

This repository contains a local Python/FFmpeg video renderer. These
instructions apply to ChatGPT, Pi, OpenCode and other coding agents.

**Never write directly to \`main\`** during the current refactor. Use the
existing \`refactor/modular-render-engine\` branch and PR #1, and do not
merge without explicit approval.

Before making or editing a video:
1. Read \`docs/AGENTS.md\` and \`docs/CLI.md\`.
2. Call \`reels-maker catalog --root . --json\` to discover usable source paths.
3. Create/edit a JSON manifest in \`projects/\`.
4. Run \`reels-maker validate <manifest> --syntax-only --json\`.
5. Run \`reels-maker validate <manifest> --root . --json\`.
6. Run \`reels-maker render <manifest> --root . --json\`.
7. Verify successful exit code and inspect the generated MP4 before claiming success.

Prefer a re-usable manifest and core renderer changes over creating a new
ad-hoc one-off Python script. Preserve original source media, audio licenses,
and existing finished renders. Only \`output/\` and \`.cache/\` hold new binaries.
The same JSON CLI contract must work without interactive input or network
access, including from terminal harnesses.

Keep visual safe zones, brand assets and sound in sync with the manifest.
For video speed, reuse scene cache and use multiple jobs only when resources
allow. Do not add model API calls or hosted dependencies to the core renderer.
