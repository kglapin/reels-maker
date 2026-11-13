# Carbon engine policies and advanced choreography

## Existing defaults

Ordinary StudioProject rendering inherits productive Carbon motion. Scene
`carbon_motion` overrides the default; false/null disables it. Project setting
`export.carbon_motion` accepts true, false/null or the existing profile object.
Explicit scene profiles win. Camera Canvas and non-Studio FFmpeg/Cairo paths
are not implicitly migrated. Recreate projects from source manifests after
changing policies; construction resolves a scene snapshot.

Optional `export.carbon_spacing: true` uses the 13-token Carbon spacing scale,
mapping xs/sm/md/lg/xl/xxl to 8/16/32/48/64/96 design units, then canvas scaling.
A role-token object overrides that mapping. This intentionally replaces those
spacing roles, not brand fonts/colors/safe areas. Optional `carbon_sequence`
adds frame-aligned text-role cues only when no authored cues already exist.
The .12s default gap and .5s span are video adaptations, not IBM specifications.

## New: bounded accent director

Set `export.carbon_director: true`, optionally `carbon_accent_limit: 1` (0..3).
Known proof/reveal/statistics/hook/opening intents are ranked deterministically.
The remaining expressive budget accounts for already expressive scenes.
Disabled profiles and `carbon_lock: true` are respected. Opting in authorizes
upgrading unlocked productive scenes. This is an authored rule set, not an
LLM, aesthetic critic or an official IBM algorithm. Resolved modes are stored
in project.scenes so normal cache keys reflect the decision.

## New: explicit role choreography in Studio manifests

```json
{"carbon_choreography":{"attention_limit":3,"roles":{
  "headline":{"relation":"reveal","segments":{"opacity":[
    {"index":1,"phase":"entrance"},{"index":3,"phase":"exit"}]}},
  "visual":{"path":{"to":[0.2,0.1],"at":1.0,"duration":0.8,"axis":"x"}}
}}}
```

Segment indices identify destination keys in an existing track. Only selected
appearance segments change; values, times and intervening holds remain intact.
Data/progress tracks are excluded. Inspect native tracks before choosing indices.

A role can instead use `adaptive: {"properties":["dx","dy"],"minimum_hold":0.8}`.
Its two-key tracks must share a time interval. Duration grows with normalized
distance and log scale change, is frame-quantized and refuses insufficient
reading room rather than compressing text or shifting narration. The formula
and .18.. .9s bounds are original video policy, not Carbon source constants.

Spatial paths offset horizontal/vertical timing (at least three frames), giving
a rounded-corner-like trajectory, not an exact circular arc. `to` is a pair of
canvas-fraction offsets from base geometry, not absolute screen coordinates.
Root nodes only; active authored translations cannot be overwritten. Adaptive,
segment and path ownership conflicts fail explicitly. Relation labels
replace/reveal/detail/result guide curve choice, not automatic layer creation.

## New: limited shared-object bridges

On adjacent scenes bind the same stable ID: `carbon_shared: {"photo":"visual"}`.
Optional outgoing `carbon_bridge_duration` defaults to .7s. Currently supported:
leaf root image, unstroked rect, or circle, same content/style and aspect ratio.
No groups, text morphs, videos, clipping, rotated/nonuniform objects, or other
scene transitions. The object must fit the rectangular content safe area.

The bridge moves/scales the source into the target's base geometry by the LAST
ENCODED frame. The target's appearance entrance/exit is intentionally removed:
a shared object stays visible, rather than fading out and reappearing. Bindings
therefore own that object's lifetime. Conflicting authored transforms or role
choreography fail. This is geometry continuity, not verified pixel identity,
occlusion, full-background continuity, or arbitrary-object morphing. Platform
UI polygons and collisions still require normal QA and actual MP4 inspection.

The source cache key includes a hash of the next scene when shared IDs match;
target changes therefore invalidate its predecessor too. Graph edits occur on
clones; errors do not half-modify original built nodes. Settled caches are
cleared. The ordinary Studio build path invokes this stage after construction.

Concurrency diagnostics report simultaneous animated roles after all edits.
They are warnings for review, not measurements of perceptual attention/taste.

## Acceptance and limits

Advanced settings are opt-in; no advanced config preserves the existing graph.
These fields belong to Studio manifests, not unchanged Creative Spec v1 schema.
The test module separates ten dependency-free policy tests from five native
graph/Studio tests. Run both, full regressions, golden comparisons and real
MP4/mobile/audio review. Do not auto-recapture fixtures or claim visual approval
from a numerical test. Full-engine native rendering is still required.

Sources for principles, not for our duration/selection algorithms:
- https://v10.carbondesignsystem.com/guidelines/motion/overview/
- https://v10.carbondesignsystem.com/guidelines/motion/choreography/
- https://v10.carbondesignsystem.com/guidelines/spacing/overview/
