# CLI contract for Pi, OpenCode and ChatGPT

The system is an ordinary subprocess. The harness may author manifests, query
media catalog and invoke documented commands; no TTY or remote model API
required.

```sh
reels-maker doctor --json
reels-maker catalog --brand asta-energy --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --syntax-only --json
reels-maker validate brands/asta-energy/projects/asta-rush-demo.json --json
reels-maker render brands/asta-energy/projects/asta-rush-demo.json --jobs 2 --json
reels-maker inspect renders/asta-energy/asta-rush-demo.mp4 --json
```

Machine contract: successful JSON on stdout with `schema_version: 1` and
`status: "ok"`; errors as structured JSON on stderr, process exit 2.
`doctor` returns exit 3 if FFmpeg/FFprobe is missing.

Brand manifests inherit `brand.json` defaults. Media paths resolve inside
`brands/<slug>/`; other brands cannot be accessed using relative traversal.
Catalog defaults to inexpensive file discovery, `--probe` inspects metadata.
A scene is encoded only on a cache miss; independent scenes may encode
concurrently. Use unique output filenames for concurrent agent jobs.

No videos or large assets should be copied into Python source code. Source media
must remain accessible locally to FFmpeg; a GitHub code connector alone does
not guarantee that video bytes are available to the renderer.

Note: original scripts in `legacy/asta-energy/scripts/` are archived and contain
Mac-only paths. Do not execute them without explicit porting.
