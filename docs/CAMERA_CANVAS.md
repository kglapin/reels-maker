# Camera Canvas — irregular editorial camera movement

**Status:** available as an opt-in Studio rendering mode, verified by CI MP4 render. Existing scene animations remain the default if this option is absent.

## Concept

Unlike scene-by-scene transitions, this mode uses **one persistent canvas**. Every photograph is placed in world coordinates before rendering. The camera moves between irregularly spaced points and rotates to match their local orientations. Earlier elements remain on the canvas and may appear during camera travel. **Each shot's typography enters only after its camera move has settled.**

## Scene schema

Add `camera_canvas` to **every** scene. Each scene still has its ordinary `duration`, `photo`, `headline`, and `subtitle`.

```json
{
  "id": "02-different-perspective",
  "composition": "statement",
  "duration": 3.15,
  "photo": "assets/rotation-02.jpg",
  "headline": "CHANGE ANGLE",
  "subtitle": "Camera arrives before the text.",
  "camera_canvas": {
    "x": 2200,
    "y": 840,
    "angle": 68,
    "zoom": 1.02,
    "layout": "photo-left",
    "move_duration": 1.0,
    "reveal_delay": 0.22,
    "reveal_duration": 0.6
  }
}
```

The example renders to video using:

```bash
python examples/generate_editorial_rotation_assets.py
reels-maker studio-render examples/irregular-camera-canvas-demo.json --output irregular-camera-canvas.mp4 --supersample 1
```

## Fields

- `x`, `y`: camera stop in **world pixels**, not screen pixels.
- `angle`: camera rotation in degrees, with unwrapped values for a continuous spin.
- `zoom`: camera scale (0.65–2); default 1.
- `layout`: `photo-above`, `photo-left`, `offset`, or `diagonal`. Determines media/typography placement within the camera-facing tile.
- `move_duration`: duration of interpolation from the previous camera stop, seconds; default 0.8.
- `reveal_delay`: pause after camera travel before typography starts; default 0.18.
- `reveal_duration`: length of typography reveal; default 0.55.

For the first scene, camera travel is zero. For later scenes, travel is eased using smoothstep; position, scale and rotation interpolate together. All image assets remain fixed on the shared world; text is not permanently burned into backgrounds until its local reveal.

## Design guidance

- Mix small and large camera moves, including off-axis paths and deliberately unequal rotation angles.
- Do not confuse irregularity with randomness. Each destination should support a clear subject and readable headline.
- Alternate dense and airy destinations; the global canvas should have intentional negative space.
- Ensure destination elements remain inside the target camera crop and platform safe zone.
- Avoid typography entrances during fast camera motion; the viewer needs a stable composition first.

## Current boundaries

- This is an **initial integration**, not yet a full automatic shot director. Placement and rotation parameters are explicitly authored.
- Typography reveal is a simple eased reveal of the local text layer. More varied kinetic typography should be integrated in a separate phase.
- Photo layouts use predefined safe-ish rectangles. Subject-aware saliency cropping and a rigorous automatic camera-safe bounds optimizer are not yet implemented.
- World size is limited to 32 million pixels to avoid runaway memory use.
- The render mode is opt-in and backward-compatible with existing Studio projects.
- Camera motion is interpolated between two defined stops rather than following a multi-control-point Bézier trajectory.
- Test status confirms backend operation and export validity, not final art-director-grade aesthetics.

Automated tests: `tests/test_camera_canvas.py`; CI: `.github/workflows/irregular-camera-canvas-demo.yml`.
