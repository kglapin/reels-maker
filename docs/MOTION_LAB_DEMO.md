# Motion Lab five-minute engine demo

This is a fictional, synthetic-media-only demonstration, not a commercial
advertisement or an approved creative delivery. It contains no customer assets
or third-party photos/video. The generated stills are stylized illustrations,
not photographs; the MP4 clips are procedural animations made locally.

## Rebuild

From the repository root:

```sh
PYTHONPATH=src python3 tools/generate_motion_demo_assets.py
PYTHONPATH=src python3 -m reels_maker catalog --brand motion-lab --probe --json
PYTHONPATH=src:tools python3 tools/create_motion_demo_manifests.py
PYTHONPATH=src python3 -m reels_maker studio-qa brands/motion-lab/projects/studio-showcase-280s.json --root . --profile review --strict --samples 6 --json
PYTHONPATH=src python3 -m reels_maker studio-qa brands/motion-lab/projects/camera-canvas-showcase-20s.json --root . --profile review --strict --samples 6 --json
PYTHONPATH=src:tools python3 tools/render_motion_demo.py
```

The output is `renders/motion-lab/motion-lab-showcase-5m.mp4` at 720×1280,
30 fps, exactly 9,000 frames. The 35-scene Studio section (280 seconds) covers
editorial, metric, photo-motion, table/chart, procedural 3D and all ten
object-driven transition effects; the 20-second Camera Canvas section shows
irregular camera stops, rotation and photo/video sources. The assembly uses the
existing Studio renderer and stream-copy segment join. The video is silent on
purpose: no music or SFX rights were introduced for this synthetic demo.

Strict technical QA is expected to report zero blocking errors. Typography
advisories are retained in the QA report; they are not hidden or treated as
creative approval. Inspect the MP4/storyboard and listen/review on a real phone
before considering any output a deliverable.
