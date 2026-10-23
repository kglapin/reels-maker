# Reels Maker — Master Plan 1.0

This document is the single source of truth for the project's backlog, priorities, order, and acceptance gates. It defines the version 1.0 release scope (must-have features), the critical dependency chain, and the concrete execution order for the next twelve work packages.

## 1. Goal and Decision Framework
Build a repeatable, brand-aware, professional motion-design video system that generates polished advertising reels from licensed, clean footage, a deliberate creative brief, and optional narrator/music, without looking like a random AI effects montage. Target workflow: brief -> source clearance -> storyboard -> editorial cues -> deterministic render -> technical QA -> visual and audio review -> approved export.

"World-class" is a creative aspiration, not a certification that CI can award. A stable render, polished visual language and human sign-off are independent success conditions. Avoid expanding the effects catalog until the core visual examples pass.

## 2. Version 1.0: Release Scope (Must-Have)
- Deterministic Python/FFmpeg CLI
- Clean multi-brand separation
- Explicit project-owned canvas, FPS and platform-safe areas
- Brand-approved typography, logo, colors and restrained visual assets
- Text hierarchy with selected emphasis and reproducible on-scene entrances
- Curated cuts/dissolves/motion wipes; frame-aware montage planning
- Separately controlled narrator and music, explicit phrase cue timing, optional ducking
- AAC output and sound-quality diagnostics
- Preflight for real source footage, provenance of already-branded clips
- Automatic syntax/integration/technical QA, actual-frame storyboard and motion-strip review
- At least one thoroughly approved clean-source flagship brand ad, reproducible on fresh workstation
- Private, access-controlled source and media strategy with recovery path for generated assets

## 3. Source-of-Truth Hierarchy
- This file: the only master backlog, priorities, order and acceptance gates
- docs/ROADMAP_STATUS.json: compact current milestone state and next action for agents
- PR #1: engineering change review and linked CI evidence
- Issue(s), if created later: individual work tickets referencing task IDs in this document, not a competing roadmap

## 4. How to Read Task Statuses
[x] Implemented with direct repository/CI evidence. A code checkbox does not certify visual approval.
[ ] Not yet accepted, even if a partial implementation is present.
Priority P0: must complete to release v1.0; P1: valuable or parity-dependent, schedule after P0 foundations; P2: separate later feature.
Work size: S (bounded change), M (several files/tests), L (significant design/integration). Sizes are relative planning aids, not delivery promises.

## 5. Critical Dependency Chain
Required sequential path:

M00 privacy/access -> M01 clean source/provenance -> M02 deterministic foundation/CI -> M03 editorial art direction -> M04 shot transitions -> M05 kinetic type -> M06 audio/visual cue integration -> M08 visual/technical QC -> M09 full-scale reliability -> M11 approved flagship and release.

Parallel, once M00/M01 are controlled: M07 multi-brand/brandbook and M10 developer workflow/storage. M12 is optional after release.

No-go rule: Do not use polished text motion to compensate for baked-in logos/captions. Obtain unbranded footage, or intentionally reuse an existing finished film without overlaying new branding.

## 6. Editorial Review Scorecard
For each delivery, record 0–4 (unacceptable, weak, adequate, good, excellent) from a human reviewer for the following dimensions, attaching sample frames and editorial notes:

Dimension    Evidence that matters
Hierarchy    The intended hero word/idea is recognized immediately
Typography    Consistent baseline, font, kerning, composition and readable body
Motion    Easing looks physical and decisive; no bounce, shake or unnecessary FX
Rhythm    Cuts, text entrances and narrator/music accents reinforce the idea
Image treatment    Good crop, exposure, color continuity, no text/object collisions
Branding    Authentic logo; appropriate clearspace and contrast; no duplicates
Audio    Speech intelligible, music supportive, balanced transitions
Narrative    Clear premise, value and credible CTA; correct claims
Platform    UI-safe framing, correct output profile and full mobile legibility

Acceptance policy: any 0/1 blocks approval. Every dimension must be at least 3 for flagship status. This is a proposed editorial rubric; thresholds can be adapted by the owner, but changes must be documented. Do not call an automatically graded reel "world-class."

## 7. Concrete Execution Order — Next Twelve Work Packages

Order    Task    Prio    Depends on    Deliverable
00    OPS-11: restore private GitHub Actions runner availability    P0 BLOCKER    Private repo settings / owner billing check    Fresh private-repo CI runner executes real test steps
01    SEC-03/05: audit access and repository exposure    P0    SEC-01    Private security checklist with no secrets disclosed
02    MED-03: inspect all 15 clips across timelines    P0    G0    Reviewed media catalog with clean/finished/unknown
03    MED-04/06: obtain and license clean source set    P0    02    Six verified unbranded shots, rights log
04    CORE-06/07: settle manifest contract and migration    P0    CI green    Schema/version tests for all 7 JSON projects
05    ART-01/02/03: build reference board and grammar    P0    03    8–12 studied clips, one visual style guide
06    TYPE-05/09/10: fix layout and frame contrast    P0    05    Approved title-render examples
07    EDIT-03/05/06: shot-aware cut/xfade comparisons    P0    03/05    Real cut matrix and glitch checks
08    AUD-05/06/07: real narrator, music and SFX    P0    03/05    Mixed test MP4 and listening report
09    QA-05/09/10/11: visual + format regression suite    P0    06–08    Snapshot and human review rubric
10    PERF-01/03/05/06: full-res benchmarks + failure recovery    P0    09    Timings, cache report, resilience evidence
11    OPS-02/06/07: archival and reproducibility strategy    P0    01/03    Private storage decision and creator runbook
12    REL-02 through REL-14: ship two approved demos and request merge    P0    all gates    Validated, signed-off version 1.0 candidate
Do not skip work packages 02 and 03. The prior successful ASTA real-footage QA had visually defective baked-in titles, so more programming alone will not meet the creative objective.

## 8. Operating Cadence for Continued Work
At the beginning of every "kontynuuj" turn:

Read docs/MASTER_PLAN.md, docs/ROADMAP_STATUS.json, Draft PR #1, and the newest GitHub Actions run.
Confirm privacy and current branch head; never assume a previous write or CI status persisted.
Select one or two bounded unchecked tasks from the next work package, with explicit dependency and acceptance.
Implement in refactor/modular-render-engine only; add targeted tests, evidence and documentation.
Run CI, inspect any failures, fix before marking a checkbox as done.
For visual tasks, inspect real output frames/videos; synthetic success is not creative success.
Update the checkbox, roadmap JSON, and PR task link with the exact commit and evidence.
Report Done / In progress / Blocked / Next with direct links; do not invent completion percentages or promise background work.
Leave main untouched until explicit approval. Do not silently publish or expose source footage.
Definition of an individually completed task
A task is complete only after (a) committed code/config/report, (b) reproducible test or inspection evidence, (c) acceptance criteria met, (d) downstream docs/status updated. Research or a speculative proposed implementation alone is not completion.

Stop/ask-for-input conditions
Ask for human/owner input only when the next step requires actual permission or unavailable licensed inputs: repository access changes, history rewrites, source media/licences, publishing rights, final creative approval or merging. Continue with independently testable tasks in the meantime.

## 9. Project and Repository Links
Merged refactor PR: [#1](https://github.com/kglapin/reels-maker/pull/1)
Current unit/FFmpeg CI: https://github.com/kglapin/reels-maker/actions
Historical evidence: docs/REFACTOR_PLAN.md
Creative negative-control findings: docs/ASTA_CREATIVE_QA.md
Typography and timing: docs/MOTION_DESIGN.md
Format and QA principles: docs/VISUAL_QA.md
Current task status: docs/ROADMAP_STATUS.json
Repository privacy is required. A live GitHub check on 2026-10-23 reported
`PUBLIC`, so the earlier 2026-10-22 confirmation is stale and owner action is
required. Existing downstream copies of content previously public remain a
separate risk to assess.

## 10. Separate native studio prototype (not a release gate)

PR #1 merged the modular renderer on 2026-10-23. A separate local branch,
`feat/motion-design-system-20261023`, contains an experimental Pillow-based
motion-design studio and an ASTA design-system sample. The prototype is not in
PR #1, has not been pushed, and does not replace the two human-review flagship
deliveries or any G0–G11 acceptance gate. Its sample output is explicitly
illustrative and silent because supplied music publication rights are not
verified. Keep it local until the repository privacy blocker and owner review
are resolved; do not characterize automated QA as creative approval.

## 11. Motion-design overhaul — remaining task list

This checklist maps the user's full motion-design brief to work that still
needs acceptance. “Partial” means code exists but the stated acceptance is not
met; no task is complete from implementation alone. Work stays local while the
privacy blocker is open.

| ID | Prio | State | Remaining work and acceptance evidence |
|---|---|---|---|
| MD-01 Reference benchmark | P0 | Partial; annotated reference board delivered | `docs/REFERENCE_BOARD.md` delivers 18 annotated reference entries with verified studio/official links (HTTP 200 / YouTube oEmbed, checked 2026-10-23), a distilled 10-rule design grammar and 10 explicit negative examples. Remaining: owner supplies the ~35.55s original ASTA reel for the before/after benchmark (method documented in the board; nearest in-repo clip is 35.392s branded `10_tracker-pv.mp4`), plus human timecode logging after manual viewing. |
| MD-02 Shared-engine migration | P0 | Partial; opt-in adapters, audio parity and cache bench pass | `kinetic-render --engine studio` adapts kinetic scenes; `render --title-engine studio` animates scene-graph overlays on original moving video. Legacy/studio contact sheets, logo and backdrop were inspected on the same reviewed CC0 clip. Added tests: identical AAC audio mix across both title engines (duration and mean-volume parity), brand-token accent/material flow into studio overlays, and a cold/warm cache benchmark on the parity clip (cold 1.67s → warm 0.12s, warm reuses the cached scene). Remaining: wider manifest coverage and default-path migration review; no default switch yet. |
| MD-03 Responsive layout/type | P0 | Partial; automated aspect matrix passed | All 13 demo scenes build and pass geometry QA in portrait, square and landscape; square/landscape MP4 sheets were inspected. Remaining: human phone review, varied copy and evidence from approved real-footage projects. |
| MD-04 Motion direction | P1 | Partial | Add only reference-backed gaps (shape morph/match cut/parallax/spring as justified); validate rhythmic variety and minimum read holds on actual footage. No speculative catalog growth before MD-01/03 review. |
| MD-05 Product visuals/assets | P1 | Partial | Build a reviewed, licensed product/icon/Lottie library with source, resolution, topic and license metadata; test product relevance and avoid duplicate shots. Lottie/dotLottie rendering is not implemented. |
| MD-06 Narration/audio | P1 | Partial; rights blocked | Spot and record manually verified word onsets for a real licensed narrator, produce a music/SFX mix, verify cue drift/loudness/true peak and listen on phone. Current SFX integration was tested only with generated tones. |
| MD-07 Narrative scene selection | P1 | Partial; explainable planner delivered | `reels_maker/planning.py` + `reels-maker plan` convert a reviewed brief into a deterministic studio-manifest draft with story roles (hook/context/benefit/process/proof/stats/cta), clamped frame-aligned duration allocation and an explicit reasoning report. Copy, metrics and contact fields must come from the brief (missing data stop the plan with actionable errors; template-default catching verified by tests). Assets must be reviewed clean sources; repeated media can never be used silently and pool exhaustion is named. Two synthetic briefs build and pass studio QA. Remaining: real ASTA brief after owner-supplied approved copy/claims, and stylistic variety review on footage the owner approves. |
| MD-08 Visual regression QA | P0 | Partial; safe/collision and 3-aspect geometry tests pass | Add studio golden frames and transition/motion-strip regression fixtures; expand the render matrix across profiles and real brand footage; retain reports with exact scene/time/frame and human review notes. Negative text deliberately raises a phone-review warning. |
| MD-09 Performance/reliability | P0 | Partial | Add reusable layer/frame cache with invalidation, cold/warm and changed-scene benchmarks, high-motion/full-resolution stress tests and recovery evidence. Current 91.24s render is one measurement, not a benchmark. |
| MD-10 Multi-brand acceptance | P0 | Partial; synthetic isolation test passed | Three temporary brand palettes/styles are tested for cross-contamination. Remaining: three real brand manifests/assets and human-approved footage/logo/typography renders. |
| MD-11 Release/owner gates | P0 | Blocked | Owner must resolve repository visibility (currently PUBLIC), confirm source/music/SFX rights, recheck marketing claims, view the outputs on a phone, score the editorial rubric and approve any release/push/merge. |

### Next unblocked local task

Continue **MD-08** with studio golden-frame and transition/motion-strip
regression fixtures, then assess MD-04 reference-backed motion gaps against
`docs/REFERENCE_BOARD.md`. The MD-07 planner exists locally but still needs an
owner-reviewed brief with real approved copy before a real-brand run.
Both new routes stay opt-in until parity and human visual
review pass. Synthetic aspect-matrix evidence does not close MD-03; phone
review of approved real-footage frames remains required.
