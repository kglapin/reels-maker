# ASTA Energy — real footage creative QA

Two **genuine ASTA video sources** are used in this controlled comparison:
`5_reels-asta-pv-dla-branzy-drzewnej.mp4` and
`8_asta-pila-realizacja-30kwp.mp4`. Both are ordinary repository media,
not stock or synthetic video. These inputs remain confined to the brand.

## What is compared

- `asta-creative-qa-cut.json`: intentional hard cut, no transition.
- `asta-creative-qa-dissolve.json`: the same scenes with a 5-frame dissolve.

Both use identical, manually curated typography, one emphasized word,
single brand color, two restrained entrance presets, a branded logo,
safe areas defined for 720x1280 and no music. This isolates the transition
choice as the only creative difference.

### Running on GitHub Actions

On a change to these demo manifests or the workflow, GitHub Actions performs
a sparse checkout of **only two media assets** plus the engine and brand
configuration, validates both project scripts under `--strict-quality`,
renders two MP4s, verifies codecs/frame counts/FPS, then exports still sheets
and 3-phase motion strips extracted from the actual decoded videos.

Get the short-lived ZIP artifact named `asta-creative-qa-cut-vs-dissolve`
from the **ASTA real-footage creative QA** workflow run. It contains:
`creative-cut.mp4`, `creative-dissolve.mp4`, their contact sheets,
their `entry/settled/exit` strips and machine-readable validation reports.

The workflow also supports manual `workflow_dispatch`, but does not run
on every ordinary refactoring commit. Do not merge this PR to main without
explicit approval.

## Human review checklist

1. Watch both videos at normal speed on a phone, initially muted.
2. Verify the logo is legible without a heavy opaque block.
3. Confirm the accent highlight leads the hierarchy, not the gradient.
4. Observe whether the dissolve contributes storytelling; if not, keep cut.
5. Inspect crop: important panels/people/installation context cannot be hidden
   by text or cut out for 9:16.
6. Check safe zones for the *actual* publishing platform and placement.
7. Verify claims, media licence and approval before external publication.

A passing technical QA is **not** an independent creative certification.
