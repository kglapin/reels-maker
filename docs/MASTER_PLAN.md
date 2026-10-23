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
Draft working PR: #1
Current unit/FFmpeg CI: https://github.com/kglapin/reels-maker/actions
Historical evidence: docs/REFACTOR_PLAN.md
Creative negative-control findings: docs/ASTA_CREATIVE_QA.md
Typography and timing: docs/MOTION_DESIGN.md
Format and QA principles: docs/VISUAL_QA.md
Current task status: docs/ROADMAP_STATUS.json
Repository privacy is required and confirmed as of 2026-10-22. Existing downstream copies of content previously public remain a separate risk to assess.