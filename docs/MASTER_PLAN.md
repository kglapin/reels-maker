# REELS MAKER — MASTER PLAN 1.0

**Status:** active, controlled refactor; private GitHub repository.  
**Verified on:** 2026-10-22.  
**Working branch:** refactor/modular-render-engine; **Draft PR:** #1.  
**Hard rule:** do not merge to main, publish media, expose a repository, rewrite Git history, or permanently remove archival material without explicit approval.

## 0. Goal and decision framework

Build a **repeatable, brand-aware, professional motion-design video system** that generates polished advertising reels from **licensed, clean footage**, a deliberate creative brief, and optional narrator/music, without looking like a random AI effects montage. Target workflow: brief -> source clearance -> storyboard -> editorial cues -> deterministic render -> technical QA -> visual and audio review -> approved export.

"World-class" is a creative aspiration, **not** a certification that CI can award. A stable render, polished visual language and human sign-off are independent success conditions. Avoid expanding the effects catalog until the core visual examples pass.

### Version 1.0: release scope (must-have)

- Deterministic Python/FFmpeg CLI; clean multi-brand separation; explicit project-owned canvas, FPS and platform-safe areas.
- Brand-approved typography, logo, colors and restrained visual assets; text hierarchy with selected emphasis and reproducible on-scene entrances.
- Curated cuts / dissolves / motivated motion wipes; frame-aware montage planning.
- Separately controlled narrator and music, explicit phrase cue timing, optionally approved ducking, AAC output and sound-quality diagnostics.
- Preflight for real source footage, provenance of already-branded clips, format/profile/rights checks and protection against silent bad exports.
- Automatic syntax/integration/technical QA, actual-frame storyboard and motion-strip review; **human creative review** for every client-ready video.
- At least one thoroughly approved **clean-source flagship brand ad**, reproducible on a fresh workstation and via documented CLI.
- Private, access-controlled source and media strategy, explicit legal/content sign-off and recovery path for generated assets.

### Not required to release 1.0

Automatic transcript inference, generative clip selection, dozens of shader presets, proprietary GUI, full cloud rendering platform, autonomous publishing, visual AI aesthetic scoring, 3D title scenes, extensive animation-template marketplace. Consider these only after 1.0 acceptance.

### Source-of-truth hierarchy

1. This file: the **only master backlog**, priorities, order and acceptance gates.
2. docs/ROADMAP_STATUS.json: compact current milestone state and next action for agents.
3. docs/REFACTOR_PLAN.md: historical architecture implementation log (do not delete).
4. PR #1: engineering change review and linked CI evidence.
5. Issue(s), if created later: individual work tickets referencing **task IDs in this document**, not a competing roadmap.

### How to read task statuses

- **[x]** Implemented with direct repository/CI evidence. A code checkbox does not certify visual approval.
- **[ ]** Not yet accepted, even if a partial implementation is present.
- Priority **P0**: must complete to release v1.0; **P1**: valuable or parity-dependent, schedule after P0 foundations; **P2**: separate later feature.
- Work size: **S** (bounded change), **M** (several files/tests), **L** (significant design/integration). Sizes are relative planning aids, **not delivery promises**.

## 1. Verified baseline and material constraints

As observed from the working branch on 2026-10-22:

- Repository visibility: **private** (verified through GitHub repository API); earlier public exposure cannot be undone retroactively.
- Branch main still at d5c67cce70a2cdbb1f27a5221ba7d6c7acead366. Draft PR #1 head: d9eab1915e6e35427c0d919c24e48093fbc37a66.
- 25 Python source modules, 23 test files, 7 ASTA project manifests, **1 actual brand** configured.
- 15 video files under ASTA footage; **not all are unbranded masters**. Two already reviewed source clips are finished promos with baked-in logos/captions.
- Ten external stock media entries are Git LFS pointers in the Git tree; do not claim full media validation until the payloads have been checked.
- Eight historical MP4 reference exports and dozens of legacy intermediates are kept for regression evidence.
- Current Git tree represents roughly **716 MB of file content**, primarily media; repository history/storage and LFS strategy remain open.
- Last checked successful main test run: https://github.com/kglapin/reels-maker/actions/runs/39818837543
- **Current HEAD CI requires attention:** after the repository was made private, run https://github.com/kglapin/reels-maker/actions/runs/39821829684 failed *before a hosted runner or any workflow step was assigned*. All three jobs show no runner name, zero steps and no accessible job logs; this does **not** establish a Python regression. Check private Actions billing/quota, account budget, repository Actions policy, and GitHub-hosted runner provisioning before claiming current CI green. Do not switch back to public.
- Audio / timing gates, cue sheets, decoded AAC onset testing and read-only LUFS/true-peak checks have code and passing CI evidence.
- Real-footage A/B cut/dissolve renders have passed **technical checks**, but visual review flagged duplicate baked-in graphics, tiny supporting text and weak contrast. Those renders are negative-control QA, **not approved advertising**.

Do not invent an overall "% complete" number from the count of implemented modules. Production acceptance is gated by **real material, quality and legal checks**, not code volume.

## 2. Critical dependency chain

**Required sequential path:**

M00 privacy/access -> M01 clean source/provenance -> M02 deterministic foundation/CI ->
M03 editorial art direction -> M04 shot transitions -> M05 kinetic type -> M06 audio/visual cue integration ->
M08 visual/technical QC -> M09 full-scale reliability -> M11 approved flagship and release.

Parallel, once M00/M01 are controlled: M07 multi-brand/brandbook and M10 developer workflow/storage. M12 is optional after release.

**No-go rule:** Do not use polished text motion to compensate for baked-in logos/captions. Obtain unbranded footage, or intentionally reuse an existing finished film *without* overlaying new branding.

## M00 — Private repository, access and security | P0 | Gate G0

Objective: make private access and preservation auditable, not just rely on the GitHub visibility label.

- [x] **SEC-01 · S** Confirm kglapin/reels-maker has private=true / visibility=private in GitHub.
- [x] **SEC-02 · S** Keep PR #1 Draft and leave main untouched throughout the refactor.
- [ ] **SEC-03 · S** Verify repository collaborators, GitHub Apps, external actions and deploy key access; remove excessive privileges with owner approval.
- [ ] **SEC-04 · M** Inventory previously public assets, archives, generated artifacts, forks/mirrors and any third-party links; document residual exposure risks.
- [ ] **SEC-05 · M** Search Git history and current files for credentials, customer records, personal identifiers, API keys and proprietary source leaks; never publish findings or secrets in PR logs.
- [ ] **SEC-06 · M** Rotate/revoke any credentials exposed in the former public repository; private visibility alone does not invalidate copied secrets.
- [ ] **SEC-07 · S** Audit Actions permissions: minimum read scopes for QA, protected artifact access/retention and avoid plaintext secrets in build logs.
- [ ] **SEC-08 · M** Establish branch protection, required checks and review policy compatible with account permissions; verify no accidental auto-merge or public release.
- [ ] **SEC-09 · S** Document who may approve branded footage, licence checks and production export, and who may merge.
- [ ] **SEC-10 · M** Preserve recoverable encrypted/private backups of canonical project definitions and media catalogue.

**Exit G0:** GitHub private visibility reconfirmed; access, secrets, backups and residual public-history risks reviewed, with corrective action completed or documented.

## M01 — Footage provenance, licences and clean masters | P0 | Gate G1

Objective: ensure every selected video clip is appropriate for new titles/branding, with its rights and content known.

- [x] **MED-01 · S** Implement reviewed asset types clean_source / finished_promo / unreviewed in catalog.
- [x] **MED-02 · S** Raise source_is_prebranded when new typography/branding is applied to reviewed finished promos in strict-quality mode.
- [ ] **MED-03 · M** Review and classify **all 15 ASTA footage clips** by sampling actual decoded frames at multiple timestamps; record observations, resolution, FPS and defects.
- [ ] **MED-04 · M** Obtain at least **6 distinct clean ASTA source shots** suitable for premium reels (wide, detailed, human/installation context), with no baked-in titles/logo.
- [ ] **MED-05 · S** Add per-asset editorial metadata (cleanliness, text-safe areas, people/face presence, rotation, source quality and crop constraints).
- [ ] **MED-06 · M** Track copyright/stock/audio/font permissions, licence type, attribution requirements, territory, commercial/reuse scope and proof of acquisition.
- [ ] **MED-07 · S** Fully hydrate and inspect **all 10 Git LFS stock payloads** before referencing them in deliverable manifests; detect missing/expired pointers.
- [ ] **MED-08 · M** Add checks for invalid media (corrupt/truncated, VFR, silent video, unexpected source audio, HDR/SDR mismatch and unusual orientation).
- [ ] **MED-09 · M** Make shot-level cropping decisions on the actual subject (panels, battery, people), not purely central crop.
- [ ] **MED-10 · S** Maintain source-vs-export distinction, including clear negative-control QA manifests not approved for marketing.
- [ ] **MED-11 · S** Add clear treatment for third-party portraits, identifiable people and customer installations (permissions/releases when required).

**Exit G1:** Every shot in flagship ad is explicitly approved as clean and licensed; no accidental overlay on finished promos; LFS sources and stock rights verified.

## M02 — Specification, determinism and core rendering | P0 | Gate G2

Objective: a portable, reliable engine that fails with clear errors, not with visually broken videos.

- [x] **CORE-01 · M** Single Python/FFmpeg engine in src/reels_maker rather than brand-specific renderers.
- [x] **CORE-02 · M** JSON scene projects, project-specific width/height/FPS, brand inheritance and relative paths.
- [x] **CORE-03 · M** Cached scene segments, hard-cut stream-copy path and parallel scene jobs.
- [x] **CORE-04 · M** Frame-quantized transitions and accurate final duration accounting.
- [x] **CORE-05 · M** Atomic publication of encoded MP4 and post-encode codec/dimension/FPS/frame/audio checks.
- [ ] **CORE-06 · S** Consolidate one versioned schema for every project field, including motion cues, audio sync, safe areas, links and deprecations.
- [ ] **CORE-07 · M** Add schema migration/backwards-compatibility tests for all seven existing project JSON manifests.
- [ ] **CORE-08 · M** Audit path boundaries, symlinks, malicious filenames, unsafe FFmpeg filter injection, resource limits and untrusted SVG/media handling.
- [ ] **CORE-09 · S** Pin and document Python, Pillow, FFmpeg, ReportLab and optional packages; record versions in every render manifest.
- [ ] **CORE-10 · M** Ensure scene-cache invalidation includes sources, logo/font assets, requested frame profile, code/schema version and rendering settings.
- [ ] **CORE-11 · S** Document expected failures and actionable CLI error JSON for missing media, missing font, wrong profile and malformed cue.
- [ ] **CORE-12 · M** Smoke-test a *clean environment* (Linux and at least one local desktop platform) from install to real output.

**Exit G2:** All manifests parse, errors are explicit, output is deterministic within documented codec/toolchain bounds, core CI is green and a clean install renders a valid MP4.

## M03 — Editorial creative direction / anti-'AI slop' system | P0 | Gate G3

Objective: make professional art direction the constraint; effects are secondary.

- [ ] **ART-01 · M** Select 8–12 licensed/reference premium promotional reels across at least 3 visual styles (corporate-energy, editorial/product, fast montage) for internal study.
- [ ] **ART-02 · M** Annotate each reference: framing, cut rhythm, timing, typography hierarchy, density, masks, easing, use of audio/SFX and end card.
- [ ] **ART-03 · S** Create **one visual grammar** for ASTA: restrained color, strong headline, purposeful accent, authentic logo and predictable information order.
- [ ] **ART-04 · S** Define headline/body/logo/SFX limits and hierarchy rules; mark novelty transitions as exceptions requiring a reason.
- [ ] **ART-05 · M** Build three art-direction briefs: fast case-study montage, considered B2B benefit explainer, narration-led promotional reel.
- [ ] **ART-06 · M** Test legibility over actual bright/dark moving frames; design contextual scrims or placement alternatives rather than using universal heavy overlays.
- [ ] **ART-07 · M** Standardize real footage grading/exposure/color continuity without automatically recoloring an entire scene green.
- [ ] **ART-08 · S** Add one creative rationale field per nontrivial transition and important emphasized text cue (why this movement matters).
- [ ] **ART-09 · M** Specify visual comparisons reviewed at both original size and realistic mobile display size; do not approve based on a 4K desktop alone.
- [ ] **ART-10 · S** Write explicit rejection examples: spinning titles, stock light leaks on every cut, random zooms, unreadable microcopy, aggressive glow, crowded compositions.
- [ ] **ART-11 · S** Define minimum hold/read times by *amount of text* and actual speech pace rather than only the existing 0.55 s hard minimum.

**Exit G3:** Three documented visual systems with reference evidence, approved design rules and one internally reviewed example for each. A test passing a linter is insufficient.

## M04 — Camera-aware shot transitions and montage | P0 + P1 parity | Gate G4

- [x] **EDIT-01 · M** Hard cut is the default; opt-in dissolve, dip-to-black and lateral motivated wipes via FFmpeg xfade.
- [x] **EDIT-02 · M** Overlap frame accounting and effect-density warnings.
- [ ] **EDIT-03 · M** Add shot-boundary metadata (movement direction, pace, dominant geometry, subject and continuity) to enable deliberate transition choice by the editor.
- [ ] **EDIT-04 · M** Define transition durations/presets for three pace classes; use ranges measured in frames and rationale per shot.
- [ ] **EDIT-05 · M** Build transition preview matrix from **real clean footage**, including match cuts, J-cuts/L-cuts where audio calls for them, not random shader demos.
- [ ] **EDIT-06 · M** Verify first/last/black-frame behavior, xfade compatibility, VFR resampling, abrupt luminance shifts and double-encoding quality.
- [ ] **EDIT-07 · L · P1** Compare historical green-flash, film-burn and other FX to reference MP4; archive or migrate only presets that pass art-direction review and licensing checks.
- [ ] **EDIT-08 · M** Verify cuts on beats/narrator accents with frame-based cue sheet and explicit crossfade offsets.
- [ ] **EDIT-09 · M** Test the same montage at 25/30 FPS with consistent cinematic pacing and without unrequested interpolated motion.

**Exit G4:** Editor approves cut-vs-effect decisions on clean footage, visual boundaries show no technical glitches, and the system does not insert transitions just to demonstrate a feature.

## M05 — World-class kinetic typography and composition | P0 | Gate G5

- [x] **TYPE-01 · M** Rich text runs with mixed emphasis, accent color, word boundaries, font-metric layout and shared baselines.
- [x] **TYPE-02 · M** Independent logo, headline fragments and supporting text layers with controlled fade/stagger/slide.
- [x] **TYPE-03 · M** Explicit cue_frames/cue_seconds for each semantic phrase plus frame-hold validation.
- [x] **TYPE-04 · M** Format-independent scaling, literal pixel safe areas and measurement of text bounds.
- [ ] **TYPE-05 · M** Add balanced multiline composition, rag control and avoid orphan/stranded single words in large text.
- [ ] **TYPE-06 · M** Introduce explicit per-run hierarchy tokens (hero, lead, secondary) to reduce arbitrary size proliferation.
- [ ] **TYPE-07 · M** Build a small vetted reveal catalog: fade, rise, wipe/mask, directional slide and editorial stagger; visually approve timing/easing curves.
- [ ] **TYPE-08 · L** Implement and benchmark genuinely needed masked text reveals (line-by-line clipping and optional directional masks); keep default rendering simple.
- [ ] **TYPE-09 · M** Test accents, Polish diacritics, kerning, ligatures, line breaks, logo clearspace and fallback font substitutions.
- [ ] **TYPE-10 · M** Add contrast testing on **multiple real frames**, not only single title-card background; provide reposition/backdrop recommendations.
- [ ] **TYPE-11 · M** Resolve collisions with faces, hands, key product details, logos, lower thirds and platform UI overlays.
- [ ] **TYPE-12 · M** Build at least 5 approved reusable typography layouts with actual exported MP4, not illustrative SVG previews.
- [ ] **TYPE-13 · M** Review all five entrance presets for velocity jumps, shaking, opacity artifacts, inconsistent baselines and excessive element count.
- [ ] **TYPE-14 · S** Separate scene titles from **subtitles/captions** with independent line length, cue timing and safe-area rules, if captions are required in first release.

**Exit G5:** Headline is dominant within one second, emphasized phrases enter on intended cues, body remains readable at mobile size, and no text overlaps important image content.

## M06 — Narration, sound design, music and timing | P0 | Gate G6

- [x] **AUD-01 · M** Independent music/voiceover sources, trim and explicit global narrator offset.
- [x] **AUD-02 · M** Optional moderate sidechain compression, AAC mix and limiting.
- [x] **AUD-03 · M** Voice source sync marks with drift tolerance and xfade-aware absolute cue-sheet.
- [x] **AUD-04 · M** Decoded AAC onset regression; read-only integrated LUFS / true peak / loudness range measurement.
- [ ] **AUD-05 · M** Test real human narration and licensed music on a flagship ad, not only synthetic sine waves.
- [ ] **AUD-06 · M** Measure dialogue intelligibility against music on phone speaker and headphones; adjust ducking attack/release and track volumes by creative brief.
- [ ] **AUD-07 · M** Add explicit, individually timed sound effects (camera shutter, subtle whooshes, click accents) with independent volume and licence records; off by default.
- [ ] **AUD-08 · M** Provide audio fades/crossfades across scene changes without truncation, clicks, unintended silence or unapproved looping.
- [ ] **AUD-09 · M** Validate source sample rates, channel maps, mono/stereo compatibility, music tails and end-of-track cut behavior.
- [ ] **AUD-10 · S** Document loudness reference as project-specific; avoid claiming any platform has one universally required LUFS target.
- [ ] **AUD-11 · M** Create audio export comparisons before/after AAC re-encode and audit true-peak overs after compression.
- [ ] **AUD-12 · P1 · L** Evaluate optional forced-alignment tooling only when manual timestamps become a true throughput bottleneck; never fake accuracy.

**Exit G6:** Human reviewer confirms meaningful word reveals coincide with real speech and that voice stays intelligible without pumping/clipping on two playback devices.

## M07 — Brandbooks and genuinely multi-brand operation | P1, required for multi-brand claim | Gate G7

- [x] **BRAND-01 · M** Independent per-brand brand.json / assets / projects and offline PDF with real ASTA logo.
- [x] **BRAND-02 · M** Website-derived brand proposal/scan with explicit review; imported findings do not overwrite accepted branding.
- [ ] **BRAND-03 · M** Create a second real brand with its own logo, fonts and colors, with rights approval.
- [ ] **BRAND-04 · M** Verify strict brand isolation in both media catalog and rendered outputs, including cross-brand path attempts.
- [ ] **BRAND-05 · M** Confirm every referenced font is installed/licensed or explicitly bundled with a safe fallback, preserving glyph metrics.
- [ ] **BRAND-06 · S** Update outdated brandbook documentation that still suggests fixed 9:16 safe areas; brandbook defines identity, not format.
- [ ] **BRAND-07 · M** Add brandbook acceptance snapshots in print and on screen; compare real logo rendering and dark/light use.
- [ ] **BRAND-08 · M** Validate at least 3 independent project formats under the same brand (portrait, square and landscape; include 3:4/4:5 profiles when required).
- [ ] **BRAND-09 · S** Document exact owner approval workflow for brand-scan suggestions and brandbook revisions.

**Exit G7:** Brand #2 produces a wholly separate legitimate MP4, no ASTA media bleed, typography rights confirmed, and PDF remains format-neutral.

## M08 — Technical and creative QA, regression and rejection | P0 | Gate G8

- [x] **QA-01 · M** JSON schema/CLI preflight and FFmpeg synthetic integration suite.
- [x] **QA-02 · M** H.264/yuv420p/FPS/frame-count/AAC verification before published export.
- [x] **QA-03 · M** Real MP4 storyboard plus entry/settled/exit motion strip.
- [x] **QA-04 · M** Text density, effect density, prebranded footage and narration-sync strict warnings.
- [ ] **QA-05 · M** Create golden frame snapshots for representative title presets at fixed font/toolchain versions.
- [ ] **QA-06 · M** Compare historic archival MP4s by sampled images, duration, typography, color profile and audio; record **intentional improvements** rather than demanding byte-for-byte equality.
- [ ] **QA-07 · L** Add automated visual diffs with tolerance for anti-aliasing/compression; avoid flaky pixel-perfect expectations across FFmpeg versions.
- [ ] **QA-08 · M** Detect unintended black frames, repeated frames, abrupt flashing/high contrast, unintended frozen shots and truncated end cards.
- [ ] **QA-09 · M** QA matrix: 1080x1920, 1080x1350, 1080x1440, 1080x1080, 1920x1080 and a small preview profile; 25/30 FPS where needed.
- [ ] **QA-10 · M** QA matrix: accent-heavy text, long Polish copy, numerical overlays, people/face shots, bright and dark footage, narration gaps and multiple transitions.
- [ ] **QA-11 · M** Define signed-off visual review rubric: pacing, hierarchy, fit to brand, readability, natural animation, composition, sound and absence of distracting FX.
- [ ] **QA-12 · M** Make CI attach evidence packages (manifest + tool versions + JSON check reports + contact/motion strips) with private, short retention.
- [ ] **QA-13 · S** Distinguish **blocking technical failures**, **blocking compliance issues** and **human editorial warnings**; no silent exceptions.
- [ ] **QA-14 · M** Add manual review record per final deliverable, with specific revision list, approved render hash and reviewer/date.
- [ ] **QA-15 · S** Inspect platform-specific UI overlays on actual publication previews; safe areas vary between placements and app UI revisions.

**Exit G8:** No P0 blocking check remains; at least three distinct actual video examples receive documented phone-size and audio reviews, not just synthetic test passes.

## M09 — Reliability, performance, reproducibility | P0 | Gate G9

- [ ] **PERF-01 · M** Benchmark 15s/30s clips at production dimensions on cold and warm caches, recording machine, threads, RAM, disk and FFmpeg version.
- [ ] **PERF-02 · M** Compare sequential versus 2/4 worker encoding to identify actual throughput and memory pressure; no unsupported "10x faster" claims.
- [ ] **PERF-03 · M** Verify first-render vs cached-render durations, correct invalidation and zero recompression for unchanged hard-cut assemblies.
- [ ] **PERF-04 · M** Measure xfade, motion layers and audio QC overhead separately; include stage-level timings in report.
- [ ] **PERF-05 · M** Add disk-space preflight, temp output cleanup on failure/cancel, limited input/output sizes and safe cache eviction.
- [ ] **PERF-06 · M** Test interrupt/resume and atomic replacement after a failed render without losing previous approved MP4.
- [ ] **PERF-07 · S** Fix packaging dependencies and reproducibility (lockfile/pinned dependency set, FFmpeg capability/version check, document font discovery).
- [ ] **PERF-08 · M** Validate on an independent workstation and CI runner with same sample projects, documenting unavoidable encoder variability.
- [ ] **PERF-09 · S** Choose sustainable acceptance targets **after baseline measurements**; measure median and worst cases rather than set arbitrary speed goals.

**Exit G9:** Documented repeatable render from fresh install; predictable resource cost; no corrupt artifacts after failure; benchmark shows realistic production throughput.

## M10 — Storage, CI, agent/creator workflow | P0 for rights/storage, P1 for convenience | Gate G10

- [x] **OPS-01 · S** Private repo and Draft refactor PR with sparse test checkouts.
- [ ] **OPS-02 · M** Decide durable storage for raw footage, stock, music, archival MP4s, and approved final exports (Git LFS vs encrypted private object store).
- [ ] **OPS-03 · M** Inventory tracked files and history sizes, preserving old evidence; **never force-push/delete history** as a casual optimization.
- [ ] **OPS-04 · M** Add checks preventing future accidental commits of enormous video files, secrets, unsupported media or unlicensed sources.
- [ ] **OPS-05 · M** Set minimal CI triggers: fast lint/tests per code change; full media regression on explicit approval/scheduled controlled run.
- [ ] **OPS-06 · S** Version/verify artifact provenance (commit SHA, source checksums, brand revision, audio mix settings, approved profile and render time).
- [ ] **OPS-07 · M** Document one practical creator runbook: select brand -> choose clean media -> create script -> validate -> render -> inspect -> approve -> archive.
- [ ] **OPS-08 · S** Keep an explicit machine-readable roadmap status and next-task pointer for future ChatGPT/Pi/OpenCode continuations.
- [ ] **OPS-09 · M** Add private delivery packages, short retention and recoverable approved masters/proxies; never put client/private media into public examples.
- [ ] **OPS-10 · S** Require each PR to link task IDs, tests, changed outputs and QA evidence; no repeated uncontrolled feature additions.
- [ ] **OPS-11 · S · P0 BLOCKER** Restore private-repository CI runner assignment: verify GitHub Actions free-minute allowance, spending budget and failed-payment blocks in account Billing; verify Settings -> Actions -> General; retry one minimal job once hosting is available. If billing is fine, investigate GitHub-hosted runner provisioning / GitHub Support. **No public-repo workaround.**

**Immediate known blocker:** Private GitHub-hosted runners failed before job initialization on 2026-10-22; verify account minute quota/budgets/permissions and re-run when available. This is **not** permission to make the repository public.

**Exit G10:** Private-access and media strategy accepted; a second person/agent can reproduce an approved reel without guessing paths, tools or permissions.

## M11 — Flagship demos, formal approval and v1.0 delivery | P0 | Final gate G11

- [ ] **REL-01 · M** Freeze the 1.0 scope after explicit review of this backlog; defer new speculative features to M12.
- [ ] **REL-02 · M** Select a complete ASTA creative brief: 1 audience, 1 offer, 1 factual claim set, 1 CTA and 1 intended placement profile.
- [ ] **REL-03 · M** Gather approved clean sources, real voiceover (if used), music/SFX licences, fonts and exact logo.
- [ ] **REL-04 · M** Produce scripted storyboard with shot list and manually spotted narrator/beat cues.
- [ ] **REL-05 · L** Render three deliberately different, restrained creative variants (editorial benefit, faster case montage, explanatory narration).
- [ ] **REL-06 · M** Compare variants to the reference set and legacy footage on meaningful creative criteria (no random FX).
- [ ] **REL-07 · M** Perform actual phone-size playback and headphone/phone-speaker listening, correcting timing, cropping and hierarchy.
- [ ] **REL-08 · M** Pass automated end-to-end delivery pipeline: manifest, sources, technical checks, source rights, audio QC, contact sheet and motion strip.
- [ ] **REL-09 · S** Have a responsible human approve copy accuracy, brand usage, media/audio licensing, faces/locations and CTA.
- [ ] **REL-10 · S** Approve one final flagship MP4 and archive the complete reproducible delivery bundle with checksums.
- [ ] **REL-11 · M** Repeat the workflow on a second independent brief (not a copy of the same composition) to confirm the engine is a system, not one handcrafted demo.
- [ ] **REL-12 · S** Publish a concise operator manual, example brand setup, known limitations and troubleshooting.
- [ ] **REL-13 · S** Require all mandatory CI checks on the final head SHA, including safe private artifact handling.
- [ ] **REL-14 · S** Request explicit approval to mark PR ready and merge; do not self-merge or change main before approval.
- [ ] **REL-15 · S** Tag version 1.0 only after merge authorization, final smoke test and rollback notes.

**Exit G11 = definition of DONE for v1.0:** Two distinct, approved, reproducible flagship deliverables; all G0/G1/G2/G3/G4/G5/G6/G8/G9/G10 P0 checks satisfied; known P1 deferrals recorded; CI green on reviewed commit; lawful private media handling; explicit owner approval. G7 must pass before describing the released system as demonstrated **multi-brand**.

## M12 — Optional post-1.0 roadmap | P2 (non-blocking)

- [ ] **FUT-01** Evaluate GPU shader transitions (GL Transitions, vetted GLSL pipeline) only when specific approved reference demands it.
- [ ] **FUT-02** Offer a motion-template gallery with verified short live video previews, not static illustrations.
- [ ] **FUT-03** Investigate word-level forced alignment of actual audio with human verification and failure confidence.
- [ ] **FUT-04** Advanced masks/subject tracking/optical flow where footage requires it; no automatic camera motion fabrication.
- [ ] **FUT-05** Source footage semantic tagging and smart shot suggestions, gated by provenance and human selection.
- [ ] **FUT-06** Structured editing UI and job queue with render progress, resumability and clip preview, if demand justifies it.
- [ ] **FUT-07** Cloud renderer / asset delivery / media lifecycle automation after privacy and cost controls are proven.
- [ ] **FUT-08** Template analytics, A/B ad publishing workflow and brand-specific performance feedback loop.
- [ ] **FUT-09** More language/localization workflows, captions and accessibility where brief requires them.
- [ ] **FUT-10** Further MLT/GLSL ecosystem experimentation only if maintainability and repeatability outperform native FFmpeg.

## 3. Release gates: stop conditions (must never be waived silently)

| Gate | Blocking evidence | What **does not** count |
|---|---|---|
| **G0 privacy** | Private visibility; reviewed permissions and exposure inventory | A single private toggle alone |
| **G1 provenance** | All used sources clean/approved, media licences recorded | A video merely existing in Git |
| **G2 engine** | Clean install + full test/MP4 verification suite | Unit tests alone |
| **G3 art direction** | Reviewed reference set, approved visual grammar | More transition presets |
| **G4 editing** | Deliberate cuts and no visible glitches | Random effect density |
| **G5 text** | Actual mobile-readable frames and timed word hierarchy | Bounding-box checks alone |
| **G6 sound** | Real voice + music approved on devices | LUFS number alone |
| **G8 quality** | Visual and audio approval; negative controls rejected | Green CI alone |
| **G9 reliability** | Repeatable full-res benchmarks and recovery | One lucky render |
| **G10 operations** | Safe private asset storage and documented reproducibility | Large files moved to another Git path |
| **G11 release** | Two accepted reels, final review, explicitly authorized merge | A Draft PR with passing Actions |

One failure of provenance/legal/privacy or a critical export check **blocks release**. Cosmetic/creative warnings require recorded human decisions; bypasses must never be silent.

## 4. Editorial review scorecard (not an AI quality score)

For each delivery, record **0–4** (unacceptable, weak, adequate, good, excellent) from a human reviewer for the following dimensions, attaching sample frames and editorial notes:

| Dimension | Evidence that matters |
|---|---|
| Hierarchy | The intended hero word/idea is recognized immediately |
| Typography | Consistent baseline, font, kerning, composition and readable body |
| Motion | Easing looks physical and decisive; no bounce, shake or unnecessary FX |
| Rhythm | Cuts, text entrances and narrator/music accents reinforce the idea |
| Image treatment | Good crop, exposure, color continuity, no text/object collisions |
| Branding | Authentic logo; appropriate clearspace and contrast; no duplicates |
| Audio | Speech intelligible, music supportive, balanced transitions |
| Narrative | Clear premise, value and credible CTA; correct claims |
| Platform | UI-safe framing, correct output profile and full mobile legibility |

**Acceptance policy:** any **0/1 blocks** approval. Every dimension must be at least **3** for flagship status. This is a proposed editorial rubric; thresholds can be adapted by the owner, but changes must be documented. Do not call an automatically graded reel "world-class."

## 5. Concrete execution order — next twelve work packages

These are the next bounded tasks, sequenced to avoid polishing the wrong footage:

| Order | Task | Prio | Depends on | Deliverable |
|---|---|---|---|---|
| 00 | OPS-11: restore private GitHub Actions runner availability | P0 BLOCKER | Private repo settings / owner billing check | Fresh private-repo CI runner executes real test steps |
| 01 | SEC-03/05: audit access and repository exposure | P0 | SEC-01 | Private security checklist with no secrets disclosed |
| 02 | MED-03: inspect all 15 clips across timelines | P0 | G0 | Reviewed media catalog with clean/finished/unknown |
| 03 | MED-04/06: obtain and license clean source set | P0 | 02 | Six verified unbranded shots, rights log |
| 04 | CORE-06/07: settle manifest contract and migration | P0 | CI green | Schema/version tests for all 7 JSON projects |
| 05 | ART-01/02/03: build reference board and grammar | P0 | 03 | 8–12 studied clips, one visual style guide |
| 06 | TYPE-05/09/10: fix layout and frame contrast | P0 | 05 | Approved title-render examples |
| 07 | EDIT-03/05/06: shot-aware cut/xfade comparisons | P0 | 03/05 | Real cut matrix and glitch checks |
| 08 | AUD-05/06/07: real narrator, music and SFX | P0 | 03/05 | Mixed test MP4 and listening report |
| 09 | QA-05/09/10/11: visual + format regression suite | P0 | 06–08 | Snapshot and human review rubric |
| 10 | PERF-01/03/05/06: full-res benchmarks + failure recovery | P0 | 09 | Timings, cache report, resilience evidence |
| 11 | OPS-02/06/07: archival and reproducibility strategy | P0 | 01/03 | Private storage decision and creator runbook |
| 12 | REL-02 through REL-14: ship two approved demos and request merge | P0 | all gates | Validated, signed-off version 1.0 candidate |

**Do not skip work packages 02 and 03.** The prior successful ASTA real-footage QA had visually defective baked-in titles, so more programming alone will not meet the creative objective.

## 6. Operating cadence for continued work

At the beginning of every "kontynuuj" turn:

1. Read docs/MASTER_PLAN.md, docs/ROADMAP_STATUS.json, Draft PR #1, and the newest GitHub Actions run.
2. Confirm privacy and current branch head; never assume a previous write or CI status persisted.
3. Select **one or two bounded unchecked tasks from the next work package**, with explicit dependency and acceptance.
4. Implement in refactor/modular-render-engine only; add targeted tests, evidence and documentation.
5. Run CI, inspect any failures, fix before marking a checkbox as done.
6. For visual tasks, inspect real output frames/videos; synthetic success is not creative success.
7. Update the checkbox, roadmap JSON, and PR task link with the exact commit and evidence.
8. Report **Done / In progress / Blocked / Next** with direct links; do not invent completion percentages or promise background work.
9. Leave main untouched until explicit approval. Do not silently publish or expose source footage.

### Definition of an individually completed task

A task is **complete** only after (a) committed code/config/report, (b) reproducible test or inspection evidence, (c) acceptance criteria met, (d) downstream docs/status updated. Research or a speculative proposed implementation alone is not completion.

### Stop/ask-for-input conditions

Ask for human/owner input only when the next step requires **actual permission or unavailable licensed inputs**: repository access changes, history rewrites, source media/licences, publishing rights, final creative approval or merging. Continue with independently testable tasks in the meantime.

## 7. Project and repository links

- Draft working PR: https://github.com/kglapin/reels-maker/pull/1
- Current unit/FFmpeg CI: https://github.com/kglapin/reels-maker/actions
- Historical evidence: docs/REFACTOR_PLAN.md
- Creative negative-control findings: docs/ASTA_CREATIVE_QA.md
- Typography and timing: docs/MOTION_DESIGN.md
- Format and QA principles: docs/VISUAL_QA.md
- Current task status: docs/ROADMAP_STATUS.json

**Repository privacy is required and confirmed as of 2026-10-22.** Existing downstream copies of content previously public remain a separate risk to assess.
