# F2 architecture audit — Master Plan 2.0

Audit basis: local branch `master-plan-2` based on `origin/main` `eb44810`;
read-only source review (2026-10-23). This records existing code versus the F2
acceptance contract; it does not claim the planned unified renderer exists.

## Existing foundations

- Creative Spec v1 is validated and deterministically compiled into Studio or
  Camera Canvas manifests. It is not yet a typed Intent -> Motion Plan -> common
  Render Graph pipeline: `src/reels_maker/creative/{spec,director,compiler}.py`.
- Studio has a renderer-agnostic retained `Node` graph with animated property
  tracks and transformed bounds (`src/reels_maker/core/scene_graph.py`). Camera
  Canvas has a persistent Pillow world and separate camera interpolation and
  renderer (`src/reels_maker/renderers/camera_canvas.py`). These remain separate
  modes and do not share the complete hierarchy/timeline API required by F2.
- Typography layout uses local FreeType metrics and wrapping
  (`src/reels_maker/textkit/typesetter.py`). It does not prove glyph-outline
  geometry or clipping safety at every animated extremum.
- The composition optimizer can reject explicitly invalid candidates and rank
  the remaining candidates with explainable weights
  (`src/reels_maker/layout/composition_optimizer.py`); the current Director
  supplies heuristic constraints, not validity derived from every rendered
  intermediate frame.
- Studio QA defaults to six representative time samples per scene and checks
  collision, rectangular safe area, text and contrast. Camera QA documents
  approximate checks. This is not keyframe-extremum plus in-between coverage of
  a shared graph.

## Planned/unsupported claims

No evidence was found that MD-201's general typed Motion Plan/Common Render Graph,
MD-202's shared local/group/world/camera/viewport transforms, MD-203 full glyph
safe polygons, MD-204 subject-retaining camera path planner, MD-205 geometry-
derived layout candidate solver, or MD-206 timeline-extremum QA are complete.
Existing Studio/Camera Canvas features are foundations, not proof of these
acceptance criteria. Camera subject detection, arbitrary vector/video object
layers, Bézier camera paths and motion-blur are not established as supported.

## F2 implementation guardrails

- Preserve Creative Spec v1 and current render modes while adding typed
  boundaries; do not silently route manifests through a new renderer.
- Fail closed on missing font metrics, unsupported transforms, or geometry that
  escapes platform-safe bounds. Keep exact calculations deterministic.
- Add small, focused tests before changing default behavior. A P0 code change
  needs both test evidence and human creative approval before being called a
  delivery.

MD-201 is now implemented additively at
`src/reels_maker/creative/pipeline.py`: immutable Creative Intent snapshot,
intent-bound deterministic Motion Plan, and timed Render Graph adapter. It
compiles back to the existing Studio/Camera Canvas manifest and does not unify
the renderer paths. Focused tests verify v1 parity and fail-closed validation.

The first MD-202 slice is in `src/reels_maker/core/transforms.py`: typed 2D
coordinate spaces, affine composition/inversion, bounded hierarchy traversal,
and world/camera/viewport point and bounds mapping. `Node.local_to_parent_transform`
now maps Studio's existing scale/rotation/translation through that shared affine
contract for bounds and QA calculations. Camera Canvas now builds its Pillow
viewport-to-world sampling matrix from the same affine type, preserving its
existing camera behavior. Synthetic tests cover nested transforms, round trips,
invalid values, singular maps, cycles/depth, Node parity and Camera Canvas matrix
parity. The renderers still do not share one object parent/child graph; this does
not complete MD-202, establish glyph-safe geometry, or implement 3D/depth.

An initial MD-203 primitive exists in `src/reels_maker/textkit/safe_geometry.py`:
it measures per-word FreeType ink bounding boxes, tests them against validated
simple safe polygons and masks, and can apply the shared affine transform. Six
synthetic/local-font tests pass. Studio QA now invokes the checker at its
existing sample frames, after node and ancestor transforms, against the layout
safe rectangle with the same 1.5px raster tolerance as the existing rectangular
check. Focused QA tests pass across portrait, square and landscape demo layouts.
This is explicitly **ink bounding boxes, not glyph outlines**; Camera Canvas is
not covered and Studio still samples six representative frames rather than all
track extrema. It does not complete MD-203.

The next dependency-eligible F2 work is to reconcile object parent/child graph
semantics across Studio and Camera Canvas, extend ink checks to placement-specific
platform polygons/Camera Canvas, and then add glyph-outline/mask geometry. F0/
MD-002 human viewing, repository privacy, and media rights blockers remain
independent; F2 synthetic work does not clear them.
