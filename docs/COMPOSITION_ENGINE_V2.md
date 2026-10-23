# Composition Engine v2 — backend rules

Status: architecture and quality specification. These requirements are NOT all implemented.

## Core principles
- Meaning before decoration. No automatic bars, dots, rings, glows, gradients, fake UI or floating icons.
- One dominant focal point per visual beat. Supporting content must not compete in size, contrast and motion.
- Layout must follow content, image subject and negative space; never scene index.
- Measure actual glyph bounds and subject bounds before placement. A rectangle assigned to text is not its actual rendered size.
- Never silently overlap, clip or shrink critical content.
- Select transitions from narrative continuity, not random presets.
- Keep source, license, crop and selection decisions reproducible.

## Scene contract
Each scene has intent (statement, proof, comparison, process, product, testimonial, CTA), primary subject, secondary content, brand tokens, duration, energy, platform safe zones and continuity anchors. Optional detected subject boxes, gaze, saliency and negative-space map must carry confidence values. If detection is unavailable, mark it unverified and request a focal point or use a documented neutral fallback.

## Layout geometry
Use normalized coordinates for composition and convert to pixels at render time. Separate canvas, platform UI exclusion zones, editorial safe region, subject preservation region and motion overscan. Default vertical editorial inset 6–9% width, then intersect with channel safe zones. These are configurable starting points, not universal standards.

Minimum adjacent text-group spacing: one spacing token. Separate unrelated blocks by 1.5–2 tokens. Keep icon-to-text and image-to-text clearance measurable. Preserve breathing room; dense layouts must be intentional. Do not position elements with arbitrary constants.

## Typography
Use a shared role-based scale and measured line breaks. Default headline 1–3 lines. Prevent orphaned words, overflow, excessive capitalization, arbitrary accent spans and pointless kicker labels. Prefer 1–2 font weights. Maintain baseline alignment and readable exposure time. Target contrast >= 4.5:1 for small text and >= 3:1 for large text, including against sampled photographic backgrounds. These are readability goals, not a formal certification.

## Asset acquisition and crop
Pipeline: semantic query -> official provider search -> license/usage check -> download/cache -> subject analysis -> candidate crops -> composition scoring -> render -> attribution ledger. Store provider, ID, author, source page, downloaded rendition, dimensions, timestamp, hash and license evidence. Respect each provider's API terms, download tracking and attribution conditions.

Analyze faces, objects, gaze, salient regions, negative space, clutter, colors and resolution where models are available. Do not pretend a center crop is semantic detection.

Generate at least five meaningful candidate treatments: full bleed, asymmetric editorial split, floating window, edge-anchored media, cinematic strip; optionally cutout, diptych or typography mask when appropriate. Never restrict media to only a background or a small card.

Cover crop: if source ratio exceeds target ratio, retain full source height and crop width; otherwise retain full width and crop height. Center around a weighted focal point, clamp to source boundaries and penalize cropped faces, eyes, hands, product labels or critical text. Reject unusable source resolution.

## Candidate selection
Reject hard violations: clipping, overlapping mandatory elements, unreadable contrast, important subject crop, insufficient resolution, unverified rights, or platform-UI intrusion.

Rank valid candidates with initial configurable weights:
- hierarchy clarity 25%;
- spacing and legibility 25%;
- subject preservation 20%;
- visual balance 15%;
- interscene continuity 10%;
- brand consistency 5%.
These are initial design hypotheses, not validated empirical values. Store per-candidate score breakdown and rejection reasons. Prefer fewer elements and less unnecessary motion when scores tie.

## Dynamic geometry
Check bounds across entrance, hold, exit and transition. Sample easing extrema, maximum zoom, rotation, overshoot and counter digit widths. Test text/text, icon/text, subject/text, subject/CTA, platform-UI and frame-edge collisions. Intentional overlap requires an explicit exemption with rationale.

Repair in order: reflow -> shift within whitespace -> adjust grid ratio -> alternate crop -> alternate composition -> remove nonessential content -> request editorial review. Do not fix all problems by shrinking text.

## Motion
Timeline must provide readable holds and coordinated choreography. Prefer anticipation, primary action and settle when semantically appropriate. Shared objects should preserve visual identity and velocity across scene boundaries. Camera moves require overscan and motion blur where appropriate. Limit simultaneous movement and avoid strobe, arbitrary spin, checkerboard dissolves, excessive bounce, constant zoom and repetitive whip pans. Strong motion is acceptable only when motivated.

## Anti-slop quality policy
Flag generic ornaments, gradients without purpose, repeated identical card grids, excessive highlights, icon confetti, meaningless metrics, irrelevant stock photography, faux interfaces, glow stacks, random transitions and competing focal points. Return issue code, node IDs, severity, time range and suggested repair. Editorial judgments are warnings by default; brand-specific exceptions require explicit opt-in.

## QA gates
A. Semantic clarity and readable exposure time.
B. Geometry and typography across 9:16, 4:5, 1:1 and 16:9.
C. Asset crop, subject retention and provenance.
D. Contact sheets at entrance, hold, peak action and transition.
E. Frame-sampled motion and collision checks.
F. Export verification: exact frames, FPS, codec, audio sync and no black gaps.
G. Human review of hierarchy, restraint, typography, crop, motion and brand fit.

Machine-readable QA record: candidate_id, layout, asset_id, crop, focal_confidence, violations, scores, editorial_warnings, sample_times, selected_reason. No critical issues; human quality target >=4/5 median on representative real scripts.

## Implementation order
P0: golden scene corpus and snapshot baselines; repair spacing and time-sampled collisions.
P1: intent schema, 5+ composition candidates and explainable ranking.
P2: source metadata, licensing, saliency and focal crop solver.
P3: integrate chosen candidate with real scene graph and renderer.
P4: shared-element continuity, camera rig and motion budgets.
P5: evaluate 20+ diverse scripts; tune thresholds from human review.

Definition of done: reusable backend implementation, passing tests, inspected real MP4s, multiple aspect ratios, verified asset provenance and human approval. A written specification or passing tests alone do not establish production quality.
