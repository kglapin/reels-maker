# Reels Maker — Professional Motion Design Roadmap 2026–2027

Status: IMPLEMENTATION ROADMAP, not a declaration that all capabilities exist. Date: 2026-10-23. Repository reviewed at main b8d47d3755139ee08e971e150dbf12dc8d1a1b40.

## 0. Product goal and definition of professional quality

Natural-language brief -> truthful storyboard -> autonomous rights-cleared media search -> art direction -> editable Creative Spec -> shot-level scene graph -> synchronised camera/typography/vector/video/audio -> real render -> visual/technical/licensing QA -> automatic correction where safe -> delivery for Reels, TikTok, Shorts and other placements.

The aim is consistently professional output, not a guarantee that every automatically generated video is artistically perfect. The system must reject under-specified, unlicensed or defective results instead of delivering bad clips and reporting success.

Quality pillars: narrative clarity, intentional variety, composition and hierarchy, legibility on phones, authored animation curves, appropriate footage, sound design, verified usage rights, brand consistency, export compliance and operational reliability.

## 1. Evidence-based current baseline

Current source contains a working Creative Spec v1 interpreter and CLI; Studio scene renderer with H.264; motionkit/keyframes; camera_canvas for one persistent world with irregular camera stops; transition engine; text typesetter; composition candidate scoring; audio mux/QA; storyboard and frame-based tests; version-pinned Lucide and Heroicons SVG support; preliminary Pexels/Pixabay/Unsplash PHOTO search adapters.

Limitations verified from source:
- Stock adapters return metadata/URLs for photos; there is no unified, fully autonomous and licensed photo/video/music/SFX acquisition and selection pipeline.
- Camera Canvas uses a CPU Pillow world and four fixed compositional arrangements; no Bézier director path, focal-object-aware clipping guarantee, full 2.5D depth or native video layers in that mode.
- The Creative Director scores deterministic heuristics, not rendered-world perceptual or artistic quality.
- Camera typography currently has a small family set; no world-class semantic glyph morphology, full kinetic paths, per-character 3D, variable font trajectories or professional shared-element typography across shots.
- Icon library covers Lucide 0.468.0 (ISC plus some MIT-derived glyphs) and Heroicons v2.2.0 (MIT). No common provider registry for additional SVG/icon/illustration packs, asset-level licenses or semantics.
- Existing QA contains geometry and timing checks but cannot ensure all intermediate-frame camera-safe geometry, subject-aware cropping, intentional rhythm, good photography or aesthetic approval.
- Large portions of prior docs/ROADMAP_STATUS.json and docs/MASTER_PLAN.md describe older milestones and are stale. Reconcile status documents; do not treat checked historical gates as proof of current flagship artistic approval.
- GitHub repository is currently PUBLIC; decide whether private source/media is a project requirement before storing client material.

The plan below supersedes the old creative feature backlog for new work. Keep old assets and client deliveries until inventoried; the user allows retiring obsolete project formats, not accidental destruction of real source media.

## 2. Motion design standard: mandatory director principles

Use animation principles from Adobe/Disney, temporal continuity, professional typography and Google's meaningful motion guidance. Explicitly model:
1. Staging: one clear visual idea and focal point per beat.
2. Hierarchy: dominant headline/subject; supports never compete.
3. Anticipation when it clarifies an impact; no mandatory fake bounces.
4. Ease-in/out plus separate speed/value curves; velocity and acceleration continuity at joins.
5. Follow-through / overlap proportionate to mass and material, not robotic synchronized stops.
6. Arcs, direction and pivots motivated by objects, not random motion.
7. Secondary action subordinate to the primary message.
8. Timing and spacing governed by distance, movement mass, phrase duration, VO and soundtrack.
9. Contrast of quiet holds and emphatic changes; breathing room for reading.
10. Continuity of objects, color, subject, movement direction and motivated scene transitions.
11. Restraint: no gratuitous bars, dots, abstract gradients, generic sparkles, every-word bouncing or arbitrary 360-degree spins.
12. Safety: avoid strobing/flashing patterns, unreadable moving glyphs and excessive large-field rotation.
13. Mobile reading: optical rather than nominal alignment; platform UI safe areas and caption clashes.
14. Honest storytelling: no invented numbers, fictitious brand endorsements, or assets falsely represented as the user's own projects.

These are evaluation rules, not automatic aesthetic certifications.

## 3. Families of animation to implement

### 3.1 Kinetic typography (P0–P1)
- Phrase-level masked reveals with baseline-safe glyph masks.
- Character-/word-/line-level stagger, independent timing and variable selector curves.
- Character convergence, tracking and kerning expansion/settle.
- Word substitution, tracked slot replacement, inline reflow and layout-resolving text shifts.
- Per-word scale/rotation/skew/opacity/blur with scene-relative semantic reasons.
- Variable font axes (wght, wdth, slnt) with licensed font support and coherent shapes.
- Text on path, kinetic punctuation, counters with units and truthful data ticks.
- Shared text-object continuity across transitions and camera stops.
- Photo/text occlusion via segmentation and z-order; typographic image masks.
- Depth-motivated 2.5D text, perspective (only if legible), collision-safe exit trajectories.
- Distinct family choice across nearby scenes; repeated patterns permitted when artistically motivated.
- Full HarfBuzz/FreeType glyph layout, Polish diacritics, font fallback, actual bounding boxes at every interpolated frame.
- Typography data model: semantic groups, animated properties, mask regions, pivots, hold/readability windows, mobile fallbacks.

### 3.2 Shape and vector motion (P0–P1)
- SVG paths, Bézier path animation, draw-on/draw-off strokes, dash offsets.
- Topology-compatible shape morphs; else safe crossfade rather than broken interpolation.
- Nested groups, pivots, per-layer transforms, fills, gradients only when artistically warranted.
- Trim paths, organic reveal, path followers, icon state changes, reusable diagrams and process illustrations.
- Scene-graph vector geometry; native vector until raster output rather than low-resolution pre-rendered icons.
- Import sanitized SVG; disallow scripts/external resources/XXE/embedded remote assets.

### 3.3 Photo/video, composites and postproduction (P0–P2)
- Keyframe crop, pan, Ken Burns, push/pull, perspective-aligned photo cards and match-cut.
- Subject-aware crop based on face/object/saliency; maintain visibility at all frame times.
- Masked foreground subject, simple background removal, depth-layer parallax, selective motion blur.
- Real stock video clip decode, frame-accurate trim, loop handling, FPS conversion, video-as-texture and PIP composition.
- In-scene tracked placements and video masks; transitions preserving object identity.
- Optional color grading and filmic noise restrained and brand-dependent.
- Procedural motion graphics: lines, ribbons, grids, shape trails, particles; no default decorative noise.

### 3.4 Camera and space (P0–P2)
- Shared infinite editorial canvas with arbitrary non-grid shot centers and angles.
- Continuous cubic Bézier camera trajectories with per-segment angle unwrap, zoom and pivot/target curves.
- Distinct stages: approach, settle, reveal, hold, prepare exit.
- Camera-target constraints, scene crop polygon intersection and rotated text outline safety.
- Conditional adaptive overscan/zoom adjustment and dynamic layout repair.
- 2.5D depth-aware z-layers, parallax and occlusion, with camera collision/blur protection.
- Optional Blender/3D renderer for genuine spatial shots, products, lighting and reflections; never fake 3D with arbitrary spins as default.

### 3.5 Transitions and editing (P1)
- Hard cuts, audio J/L cuts, motivated wipes and reveals.
- Whip pans, camera carryover, match move, zoom-through, photo-to-type shared element, mask takeover.
- Subject- and motion-vector-aware matching across clips; avoid random pixel dissolve as default.
- Animated data visualization is a **first-class Data Motion & Infographics Engine** and an explicit **P0 workstream**, not a small transition preset. See [DATA_MOTION_DESIGN.md](DATA_MOTION_DESIGN.md). Start with accurate chart/table primitives, mobile readability and exact data lineage; then extend to line/bar/donut/waterfall, heatmaps, rankings, Sankey, table sorting, chart-to-table morphs, progressive disclosure and beat-aware data storytelling.
- Optical interpolation optional; do not invent motion frames on product photos or introduce distortions silently.

## 4. Style system / art direction catalog (P0)

Establish 8–10 style families with tokens and reference footage:
- Editorial premium / Swiss typography: restrained color, asymmetry, scale/negative space.
- Contemporary kinetic advertising: strong claim hierarchy and controlled dynamic timing.
- Documentary / cinematic: photographic storytelling, slower moves, motivated reveal.
- Product minimal / luxury: light, detail, softness, no needless gradient decoration.
- Social-native/UGC: recognisable narrative, human presence where relevant, subtitles.
- Tech/data storytelling: evidence-led diagrams, calibrated iconography.
- Playful/organic: carefully used elastic timing, illustration and secondary motion.
- Mixed-media/collage: torn edges, cut-outs, layered editorial placement, intentional paper grain.
- Optional premium 3D / isometric: only when footage and renderer capabilities support it.

Every style defines allowed fonts, sizes, line-height, palette, layout density, photo treatment, preferred motion families, easing, camera behaviour, audio motifs, forbidden effects, logo/CTA behaviour and budget of visual complexity.

Do not assemble style by random mixing. Build a reference library with verified visual examples, annotated motion moments, and rejection examples.

## 5. Autonomous stock/asset acquisition (P0)

### 5.1 Provider priority and legitimate APIs

PHOTO: Pexels (official photos API), Pixabay (official images API), Unsplash (official images API with hotlink/download tracking), Openverse (openly licensed images, item-level confirmation), Wikimedia Commons (API imageinfo/extmetadata per file).

VIDEO: Pexels Video API (current endpoint /v1/videos), Pixabay videos API, Wikimedia video where eligible. Add own footage and client-provided films. Mixkit and Coverr can be supported only through authorized/licensed integrations or manual import; do not assume a public search/download API.

SFX: prioritize a curated rights-verified internal CC0/commercial-safe library and original procedural Foley. Freesound API is available but commercial API usage needs provider permission/license. Openverse audio + Commons can supplement after item-level checking. Mixkit SFX license permits incorporation into commercial video but prohibits redistribution as a standalone asset library; use authorized import, not undocumented scraping.

MUSIC: curated, commercially cleared tracks under genuine cross-platform synchronization/use rights (CC0 or suitable CC BY with attribution, direct commercial licenses); search Openverse/Commons with original-source verification. Pixabay music requires checking Content ID risk and an authorized acquisition path; the documented Pixabay API primarily covers image/video, not a reliable public music/SFX download API. Do not assume Jamendo API commercial rights are free; it distinguishes paid commercial use. Meta Sound Collection and TikTok CML are placement/repertoire specific: never automatically export their restricted music for every other platform.

SYNTHETIC: generate simple original click, whoosh, riser, hit and transition sounds using local synthesis where suitable; store composition/reproducibility and verify loudness.

No scraping in violation of provider terms. No using free-as-in-gratis in place of license clearance.

### 5.2 Multi-provider asset broker

New interfaces: ProviderAdapter.search, get_metadata, rights_check, download_authorized, rate_limit_status, explain_failure. Provider capabilities include media kind, authentication, returned rights, geographic limits, mandatory attribution and API download conditions.

Workflow per scene:
1. Derive keyword/synonyms from script, industry, region, mood, real object.
2. Search allowed APIs in parallel with cache, rate limits, timeout and retries.
3. Apply safe-search, topic consistency, commercial-use policy and optional people/brand-release filter.
4. Collect candidates: dimensions, length, orientation, freshness, tags, author, URL, license/version and evidence timestamp.
5. Rank by semantics, photographic quality, subject, negative space, crop retention, resolution, color continuity and duplication avoidance.
6. Download permitted variants only through compliant methods; hash, scan/validate, normalize and transcode.
7. Store per-media provenance and rights terms, photographer/credit obligations, platform permissions, change log and provider download event.
8. Fall back to another eligible source if rights cannot be verified; otherwise require user-supplied assets and refuse unsafe delivery.
9. Keep caches controlled and private; never resell providers' downloaded stock as a standalone catalog.

Asset manifest minimum: ID, type, original/source page, provider, creator, license ID/link/version, usage context, allowed platforms, attribution text, download date, expiry/revocation, model/property release uncertainty, content ID status, checksum, exact local derivative paths, transform recipe.

### 5.3 Image/video intelligence

Vision embeddings for semantic fit, duplicate filtering and ranking; object/face/saliency masks; color harmony; empty-space estimation for text; object retention over a clip; reference-aware framing; 3–5 crop candidates; reject clipping/low resolution. Store subject masks and focal coordinates with provenance; user may override.

Video analysis: shot boundaries, usable in/out points, camera motion direction, face/subject stability, loudness, lighting, technical compression, resolution, frame rate and visual continuity. Match shot energy and direction to scene plan.

## 6. SVG & icon library policy (MANDATORY, P0)

### Approved initial providers and source-level conditions

- Lucide (ISC; some Feather-derived glyphs carry MIT notices) — default clean outline; current implementation exists, pinned 0.468.0.
- Heroicons (MIT) — outline/solid; current implementation exists, pinned v2.2.0.
- Tabler Icons (MIT) — large 24px-grid outline/filled catalog; add pinned local adapter.
- Phosphor Icons (MIT) — thin/light/regular/bold/fill/duotone; add style-weight-aware adapter.
- Google Material Symbols (Apache-2.0) — extensive configurable optical/fill/weight variants; add if visually appropriate.
- Iconify (MIT framework ONLY; icon packs have their own licenses) — use as discovery/metadata bridge, permit only audited icon sets.
- Simple Icons — brand logos only, with individual icon license/trademark verification; never infer universal clearance from project's CC0 notice.
- SVG Repo — mixed individual licenses; manual/provider-verified assets only; no blanket automatic approval.
- Remix Icon — switched to custom Remix Icon License v1.0 in January 2026; review precise terms and version before any import; do not treat all versions as Apache-2.0.
- OpenMoji (CC BY-SA 4.0) and other illustrated/icon packs — optional and license-gated; avoid generic emoji styling in premium brand reels.
- unDraw: free use in a film may be permitted, but its 2026 license restricts automated scraping/search/link/download integrations without permission; no autonomous provider integration by default.
- Storyset: free content requires attribution (or a suitable paid license); authorized manual ingestion, not unlicensed automatic scraping.

### Icon design rules

Choose one primary icon family per brand/film; permit mixed libraries only with a proven optical equivalence and a documented reason. Normalize viewBox, optical sizing, baseline, caps/joins, stroke widths, corner radius, semantic size, monochrome palette, alpha and layer ordering. Default to a real, relevant symbol; zero icons is preferable to visual noise.

Meaning-driven icon selection: semantic tags/synonyms, pack availability, clarity at 9:16 phone scale, brand compatibility, no misleading symbols, no redundant icons beside obvious text. Preserve SVG vector paths as long as possible. Animate purposeful draw-on, trim, fill/outline state, turn, path following or topology-safe morph. Avoid perpetual spin, emoji-like clipart, random sparkles and decorative scatter.

Security/rights: pin package release, retain upstream license notices, validate per-symbol rights for mixed sets, sanitize SVG XML and references, block external loads/scripts/foreignObject/XXE, cap complexity/path count/file size, checksum downloaded source, make offline deterministic renders possible. Icon cache may include legal metadata but may not be redistributed in violation of upstream rules.

Implement IconRegistry with fields: pack/version/license/style/grid/stroke/weight, SVG source, provider URL, semantic tags, commercial allowed, attribution requirements, allowed transforms, hash, cached export. Provide an IconDirector returning explainable suggestions and 0–3 relevant icon candidates, never a hallucinated icon name.

Acceptance: import and render at least 25 representative SVGs across three packs; compare raster/rotated/animated frames at 1080p; no injected resources, clipping or inconsistent visual weight; track license notices in export provenance.

## 7. Creative Engine / interpreter v2 (P0)

Separate Creative Intent from Motion Plan and technical Render Graph.

Creative Intent: narrative promise, audience, platform, brand, genre/style, scene purpose, time budget, facts, mandatory copy, approved media/rights, emotional energy.

Motion Plan: scene hierarchy and shot candidates, actual photos/video/icons/music IDs, layout constraints, choreography families, camera trajectory, synchronized sound cues, reading holds, transitions, rationale and alternative plans.

Render Graph: normalized coordinate spaces (world, group, camera, viewport), typed element/property tracks, easing, path/mask bounds, deterministic content-addressed asset IDs and frame-accurate timing.

Architecture:
- Capability registry advertises only executable versioned features and their restrictions.
- LLM emits constrained schema, not ad-hoc Python code; validate and compile with explicit errors.
- Director proposes 3 varied whole-film storyboard/animation plans, not 3 individually random layouts.
- Constraint solver rejects invalid layouts before choosing a favorite.
- Beat planner drives camera/media/typography from a common temporal rhythm.
- Explain why each animation and icon/photo was chosen.
- Versioned Creative Spec edits by scene ID and partial re-render cache.
- Content grounding: no invented client footage, statistics or music permissions.
- Risk-aware render gate: STOP or ask for approved alternatives if required data/rights cannot be established.

## 8. Real layout solver + camera-safe geometry (P0)

Hard constraints at all critical and interpolated frames:
- All essential text glyph outlines (not only text rectangles) inside placement-specific safe polygons; check transformed bounds after rotation/skew/zoom/overshoot.
- Masks do not cut diacritics, ascenders or descenders.
- Foreground subjects and product logos remain visible across crop and camera travel.
- Text/image intersections intentional only; overlap is rejected when it harms legibility.
- Minimum touch? Not needed for rendered video. Instead optical spacing and visual readability at typical phone size.
- Balanced negative space, modular typographic baseline/grid and deliberate asymmetry.
- Camera stop centers and pivots guided by visual focal anchors, not only regular axes.
- Source image resolution sufficient for maximum zoom and selected crop.
- Strong contrast with real post-composited frame, not just configured color tokens.

Generate layout candidates with hard-reject filters + weighted, calibrated aesthetic scores; use crop/subject/semantic continuity costs; expand masks/overscan where needed; replan if nothing is safe.

## 9. Audio Director (P0–P1)

Autonomous legal music and SFX search; classify genre, BPM, mood, instrument density, safe platforms, claims risk, license/attribution, duration and approved use.

Track analysis: beat/onset, phrase changes, quiet gaps, perceived energy and speech conflicts. Plan animation landmarks on relevant accents without forcing every entrance to a beat. Add Foley for camera whoosh, image shutter, contact/impact, UI action, ambient textures; avoid repetitive toy-like whooshes.

Sound graph: independent voice/music/ambience/SFX buses; crossfades, sidechain ducking, de-esser/limiter where justified; multi-platform loudness profiles based on measured reference and listening, not universal arbitrary LUFS. Validate clipping, true peak, start/end tails and unwanted silence. Record Content ID/licensing metadata. Provide intelligible captions with accurate timestamps and no overlap with UI safe zones.

## 10. Social media deliverables (P0)

Profile registry per PLACEMENT, not generic 'vertical':
- IG/FB Reels, IG Stories, TikTok In-Feed, YouTube Shorts;
- optional Feed 4:5, square 1:1, horizontal 16:9 and 3:4 as requested.
- 1080×1920 9:16 H.264/AAC as baseline master; 30 fps, optional 60 fps for selected effects; preview 540×960 or 720×1280.
- Format-aware composition reflow, never simple cropping of the same 9:16 scene for every target.
- Source-of-truth UI overlays/safe-area templates per platform, ad placement, CTA and date; avoid hardcoded single percentage for all placements.
- Strong first-second hook, clear problem/benefit/proof/CTA as appropriate to campaign; visually appropriate human/product focus and honest brand claims.
- Subtitles and locale-specific text with optional exports without burned captions for platform-native subtitles.
- Validate output codec/resolution/frame count/pixel format/audio/channel, color space and true mobile readability.
- Verify cross-platform music rights separately when producing the same video for multiple destinations.

Platform references: Meta Reels business guide, TikTok business ad guide and safe-zone templates, Google/YouTube upload/ads specs. These change and must be refreshed by the provider profile module.

## 11. Quality gates / self-repair (P0)

G0: Brief truth/facts/brand constraints.
G1: License/platform rights and asset provenance; strict no-go for missing permissions.
G2: Asset readiness (resolution, file health, color, video duration, source credibility).
G3: Storyboard narrative and motion variety.
G4: Constraint-based geometry at camera/typography extremes, after masks and post-compositing.
G5: Sound timing and mix; safe flashing/motion; dialogue and subtitles.
G6: Actual-frame/contact sheet/motion-strip analysis, not manifest-only.
G7: Export/codec/stream/metadata and device safe-zone verification.
G8: Review score with reasons; redo specific scenes, never conceal failure.
G9: Optional human approval before client paid ad publication.

Automated correction loop: detect -> classify -> select minimally invasive correction -> re-render only affected scenes -> compare before/after -> accept only if measurable improvement and no new regressions. Cap attempts, report unresolved warnings and offer alternatives. No infinite autonomous retries.

Golden set: at least 24 deliberately varied example reels, spanning 6 styles, different media types, 3+ brands, Polish diacritics, all platform targets and demanding edge cases. Human A/B reviews rate hierarchy, craftsmanship, rhythm, relevance and audio; technical success cannot pass this creative gate alone.

## 12. Architecture, performance and operations (P0–P1)

- Normalize Studio, camera_canvas and media clip compositing onto one typed frame/timeline interface, rather than separate ad-hoc renderers.
- Introduce transform hierarchy (local -> group -> world -> camera -> viewport), property curves, transition boundaries, plus object IDs across scenes.
- Keep PIL/CPU renderer for regression/preview; evaluate Skia/GPU-based render or FFmpeg filter graph for final complex effects, profiling first.
- Adaptive supersampling, interpolation, subframe motion blur, color management, font shaping and deterministic alpha compositing.
- Streaming tiles and per-shot render caches rather than a single huge RGBA world; media memory and max 32MP world are current constraints.
- Separate asset fetch workers, layout analysis, render workers, export verification, and artifact storage; concurrency/rate budgets.
- Versioned immutable manifests, dependency locks, content hashes, audit logs, minimal privileges, no API keys in manifests or CI logs.
- Preserve source media outside Git for larger libraries; encrypted and backed-up object storage with rights/retention policy.
- Resolve repo visibility policy (public currently) before adding confidential client data.
- CI matrix for tests, 1080x1920 renders, CPU portability, Polish fonts, video/audio licenses, visual regressions and provider mocks.
- Older roadmap entries must be reconciled to truthful status; don't report completed features from local/unmerged prototypes.

## 13. Execution program and dependencies

### P0-A — truth, catalog, and creative quality baseline
MD-001 Inventory existing modules, deprecated pipelines, media/license state and identify single runtime of record.
MD-002 Establish 24-shot golden reference suite with human annotations and failure examples; store in golden manifests.
MD-003 Build public CapabilityRegistry v2 incl icon packs, stock providers, audio, current feature flags and limitations.
MD-004 Establish licensed asset ID/provenance schema and default rights policy; block unreviewed footage/music.
MD-005 Reconcile docs/MASTER_PLAN.md, docs/ROADMAP_STATUS.json and source status, especially repository privacy and client licensing.

DONE: one truthful supported-feature catalog, signed baseline demos, explicit current gaps and no contradictory roadmap claims.

### P0-B — media broker and icons
MD-101 Implement Pexels and Pixabay photos+videos API adapters, Unsplash compliant photo adapter, Wikimedia/Openverse adapters.
MD-102 Add per-provider credentials, quotas, backoff, retries, cache, provenance, rights decisions and authorization tests.
MD-103 Implement image/video discovery ranking, alternate search fallback, download/verification/transcoding.
MD-104 Implement icon packs Lucide/Heroicons/Tabler/Phosphor/Material with pinning, safe SVG, semantic selection, cache and legal notices.
MD-105 Implement curated cross-platform-safe music/SFX packs and licensed SFX/music source adapters.
MD-106 Produce provider mock and limited live end-to-end tests; stop if unavailable or no rights.

DONE: from a legitimate brief, acquire a real photo, a real video, a meaningful SVG icon and rights-cleared audio autonomously, each with full traceable provenance.

### P0-C — shared scene graph and solver
MD-201 Typed Creative Intent -> Motion Plan -> Render Graph.
MD-202 Common hierarchy for 2D/video/vector/text/camera; reconcile Studio and Camera Canvas.
MD-203 Actual glyph shaping, text fit, multi-line wrap, mask bounds and platform safe polygons.
MD-204 Camera path planning, arbitrary positions, controlled rotation and subject retention.
MD-205 Layout candidate generator, hard-reject invalid placements, soft artistic scoring and explainable choice.
MD-206 Transform- and timeline-sampled QA at every keyframe extremum and representative in-between frames.

DONE: no essential typography cut in approved golden scenes, regardless of orientation/camera stop/move.

### P0-D — professional type/vector/video motion
MD-301 Implement at least 8 genuinely distinct text mechanism families with purpose and variation control.
MD-302 Implement grouped timing/easing curves and semantic text hierarchy with quiet holds.
MD-303 Native SVG path/trim and icon state change animations.
MD-304 Native video layer in Camera Canvas and conventional Studio, real trim/masks/crop.
MD-305 Motion-blur/overscan improvements and shared-element transitions with real object continuity.
MD-306 Polish typography regression, cross-aspect ratio checks and multi-family demo approval.

DONE: visual director signs off on photo, video, text and icon demo scenes, not only technical tests.

### P0-DATA — animated charts, tables and reliable data storytelling

See the dedicated [Data Motion & Infographics Engine specification](DATA_MOTION_DESIGN.md), which defines **DM-001–008 P0**, **DM-101–108 P1** and **DM-201–204 P2** with acceptance and regression tests.

- DM-001–003: ingest real CSV/JSON/XLSX data, verify numeric integrity and semantics, choose visualization by data relationship.
- DM-004–006: create native vector bars, time series, ranking, counters, stacked proportions **and first-class tables**; animate row/column reveal, sorting, callouts and truthful value changes.
- DM-007: guarantee data labels, units, zero/reference axes, color contrast and mobile/camera-safe typography.
- DM-008: create approved real-data social video examples (marketing, PV/energy, finance), with complete data traceability.
- P1: waterfall, heatmap, funnel, Sankey, table-to-chart morph, responsive data storytelling and audio sync.

**Acceptance gate:** verified source-to-frame numerical identity; no misleading scales, invented values, cropped labels or unreadable multi-column tables; visible story insight and tested mobile playback.

### P0-E — audio, social, final QA
MD-401 Autoselect legal cross-platform audio; music and SFX compatibility filtering.
MD-402 Beat/onset/cue model for animation/VO/SFX, bus mixing, ducking, loudness QC.
MD-403 Platform profile registry, safe-zone masks, captions/subtitles and locale adjustments.
MD-404 Frame-based quality repair loop, deterministic rerender, limited retries, audit report.
MD-405 Full HD 1080x1920 30fps master + review/square/landscape and audio validation.
MD-406 End-to-end brief->assets->render->rights/quality review->deliver test in a fresh runner.

DONE: output contains truthful licensed source credits, working sound, legible content and tested destination profile.

### P1 — higher creative sophistication
MD-501 Photo/subject segmentation and consistent 2.5D parallax.
MD-502 Character geometry/tracking/morph, variable fonts, per-character 3D only as meaningful accent.
MD-503 Rich SVG shapes/morph and tracked object animation.
MD-504 Bézier camera travel, speed profile control, focal anchor interpolation and spatial motion blur.
MD-505 Larger layout style library + stronger rhythm/style reference matching.
MD-506 Video motion matching and source quality ranking.
MD-507 Multi-scene audio dramaturgy and adaptive timing without over-synchronization.
MD-508 Creative Director renders 3 different storyboard candidates and chooses with measurable evidence.
MD-509 Human-feedback preference library and template learning only with authorized/licensed reference assets.
MD-510 Support natural-language revisions with stable shot identity and partial render caching.

### P2 — optional studio-grade extras
MD-601 Real 3D/Blender product scenes and camera lighting, not simulated planar rotations.
MD-602 Depth maps / object tracking / compositing, advanced relighting only with approved models.
MD-603 Editable motion path GUI and scene graph visualization.
MD-604 Collaboration/approval portal, comparison slider, shot comments and release history.
MD-605 Cost-aware GPU render farm and brand-domain style optimization.

## 14. Release acceptance criteria

Initial test set: minimum 24 reference reels, at least 3 unrelated brands and 6 style families. Evaluate with human reviewers at phone scale.

Required P0 acceptance:
- 100% tested projects have auditable commercial/platform rights for each media item; unknown rights are blocked.
- 100% essential typography and logos inside effective destination safe areas on approved frame samples including high-velocity/interpolated frames.
- 100% final delivery exports pass codec/FPS/frames/audio and sanity checks.
- No 3 identical consecutive entrance families unless deliberate and documented.
- Each reference clip has at least one meaningful photo/video/icon/text cue and art-director justification for non-trivial motion.
- At least 3 scene candidates considered when the creative layout is underdetermined, and rejection reasons are recorded.
- Input Polish typography never loses accents/glyph fragments due to masks, line wrap or rotation.
- Video-only requests produce genuine moving footage rather than silently degraded still-image slideshows.
- All media acquired without scraping unapproved sources and without substituting unlicensed tracks.
- Final references are signed off by a human motion-design reviewer on rhythm, hierarchy, craftsmanship, visuals and audio.
- The system can refuse or request another source when quality would otherwise be unacceptable.

Metrics to track (calibrate from baseline): pipeline success rate, per-asset search success and rights failure, scene QA error incidence, human acceptable-first-pass rate, visual complexity density, variation entropy, average render cost/time, cache hit rate, revision count to approval, reported platform issue rate. Do not label any benchmark as achieved until CI plus human review confirms it.

## 15. First implementation sequence

1. Replace stale roadmap claims with live code audit and gold-standard demos.
2. Add rights-aware asset model and provider registry, including legal SVG/icon sources.
3. Implement automatic stock photo + real video selection/acquisition with provenance.
4. Add rights-safe audio source bank (legal SFX/music) and explainable selection.
5. Rebuild camera-safe layout and typography geometry atop one transform graph.
6. Expand high-impact type/shape/vector/video primitives; test at 1080p.
7. Integrate intelligent shot pacing/camera trajectories and audio cues.
8. Implement frame-level QA and narrow self-repair.
9. Add platform-specific exports, mobile device approval, and real-life client campaigns.
10. Only then expand optional 3D and generative effects.

Do NOT undertake P2 flashy effects before safe high-quality P0 photo/video/type/audio clips pass reviewed references.

For data motion and chart/table animation: Financial Times Visual Vocabulary, Datawrapper responsive charts, Heer–Robertson animated statistical transitions and WCAG 2.2 non-text contrast. Detailed links in [DATA_MOTION_DESIGN.md](DATA_MOTION_DESIGN.md).

## 16. Verified public references (checked 2026-10-23)

Motion: https://www.adobe.com/creativecloud/animation/discover/principles-of-animation.html
https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html
https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/speed-between-keyframes/speed.html
https://m1.material.io/motion/duration-easing.html

Stock photos/videos: https://www.pexels.com/api/documentation/ ; https://www.pexels.com/legal-pages/license/ ; https://pixabay.com/api/docs/ ; https://pixabay.com/service/license-summary/ ; https://unsplash.com/documentation ; https://unsplash.com/api-terms ; https://docs.openverse.org/ ; https://www.mediawiki.org/wiki/API:Imageinfo

Rights/audio: https://freesound.org/docs/api/terms_of_use.html ; https://mixkit.co/license/modal/sfxFree/ ; https://www.tiktok.com/legal/page/global/commercial-music-library-user-terms/pl ; https://www.facebook.com/help/instagram/402084904469945 ; https://creativecommons.org/faq/index.html ; https://pixabay.com/service/faq/

Icons: https://github.com/lucide-icons/lucide/blob/main/LICENSE ; https://github.com/tailwindlabs/heroicons ; https://tabler.io/license ; https://github.com/phosphor-icons/core/blob/main/LICENSE ; https://developers.google.com/fonts/docs/material_symbols ; https://github.com/iconify/iconify ; https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md ; https://www.svgrepo.com/page/licensing ; https://github.com/Remix-Design/RemixIcon/issues/1069 ; https://undraw.co/license ; https://storyset.com/faqs

Platform: https://www.facebook.com/business/ads/facebook-instagram-reels-ads ; https://ads.tiktok.com/help/article/video-ads-specifications?lang=pl-PL ; https://support.google.com/youtube/answer/15424877 ; https://support.google.com/google-ads/answer/13547298

Technical: https://github.com/harfbuzz/harfbuzz ; https://librosa.org/doc/main/api/generated/librosa.beat.beat_track.html ; https://ffmpeg.org/ffmpeg-filters.html ; https://www.w3.org/WAI/WCAG22/Understanding/three-flashes.html ; https://tech.ebu.ch/publications/r128s2
