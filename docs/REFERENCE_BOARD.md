# Motion-design reference board (MD-01)

Backlog item **MD-01**, priority P0. Companion documents:
`docs/REFERENCE_ANNOTATIONS.md` (our own ASTA projects), `docs/REFERENCE_REELS11_ANALYSIS.md`
(kinetic primitives gap analysis), `docs/VISUAL_GRAMMAR.md`, `docs/MOTION_DESIGN_SYSTEM.md`.

## Rules for using this board

1. **Study craft, never copy content.** Every reference is another brand's paid advertising.
   We may study timing, composition grammar and choreography. We must never reuse their
   footage, music, scripts, claims, palettes or character designs. Nothing from this board
   may be shipped in a render without owner approval and licence review.
2. **No invented timecodes.** Each entry's annotation is at craft level. The timestamp
   column stays `—` until a human has watched the specific clip and logged a verified
   moment in `docs/REFERENCE_ANNOTATIONS.md`. Never guess a timecode from memory.
3. **Local-only repository.** Public links are quoted for team study only. Do not commit
   downloaded video/audio bytes of licensed campaigns into this repository.
4. **Technical acceptance ≠ creative acceptance.** Extracted grammar informs our motion
   presets; the owner still reviews every ASTA render on a phone against
   `docs/REVIEW_RUBRIC.md`.

Links marked `[verified 2026-10-23]` were checked by HTTP fetch (studio page, status 200),
or via YouTube oEmbed (title + channel confirmed).

## Annotated reference board (18 entries)

| # | Studio — Work | Client / Year | Type | Verified sources | Craft takeaway for reels-maker | Timecode |
|---|---|---|---|---|---|---|
| 1 | **BUCK** — *Get an Airbnb: "Surrounded"* | Airbnb / 2025 | CG miniature world, 0:30 broadcast | buck.co/work/get-an-airbnb [v]; YouTube `sNfluqvz1j4` ("Get an Airbnb – Surrounded", BUCK channel) [oEmbed]; stashmedia.tv review 2025-03-02 [v] | A single playful metaphoric world ("mini-land") that evolves over a campaign instead of new visual language per spot — our scenes should read as one system, not 13 one-offs. Practical technique note: procedural detail made to feel handcrafted ("artfully imperfect") is what separates studio work from template motion. | — |
| 2 | **BUCK** — *Oura: Ring True To You* | ŌURA / 2025 | 3D product film | buck.co/work/oura-ring-true-to-you [v]; YouTube `ijxJXSNIcUM` ("Oura Ring 4 Ceramic — Ring True To You", ŌURA channel) [oEmbed] | Product heroisation: extreme material close-ups before any data appears. Maps to our `media.focus_crop` + slow push-in before stat overlays; never over a pre-branded plate. | — |
| 3 | **BUCK** — *Microsoft Surface* | Microsoft | Product/typography CG | buck.co/work/microsoft-surface [v] | Interplay of thin type over hardware: type enters only after the hardware gesture settles. Supports our rule: overlay cues start on/after scene-start boundary, not riding a moving crop top-down. | — |
| 4 | **BUCK** — *Spotify Expression Illustrations* | Spotify | Brand illustration system | buck.co/work/spotify-expression-illustrations [v] | An illustration system that makes every frame recognisably one brand without a logo burn-in. Directly validates our `brand.json`-driven palette/typography isolation goal (MD-10): expressiveness must come from the system, not baked graphics. | — |
| 5 | **BUCK** — *Adobe MAX 2023* | Adobe / 2023 | Icon-led 3D (AI theme, hands) | buck.co/work/adobe-max-2023 [v] | A few icons + one strong motif ("hand") carried across many formats. For ASTA: pick one motif family per campaign (e.g. energy flow) instead of mixing five decorative overlays. | — |
| 6 | **Ordinary Folk** — *Google Gemini launch* | Google / 2024 | 2D animated text, 1:14 | ordinaryfolk.co/project/gemini [v]; YouTube `hsOyJdsXdp4` ("Google Gemini Apple Launch – Ordinary Folk") [oEmbed]; ordinaryfolk.co credits music "Actual Magic", music "Midnight Riot – That New Thing" (Vimeo v913062540) [v] | Masterclass in *animating text to mean something*: words move in the direction of their sense, with generous holds. Their credits also show real licensed music practice — our command-promo texts operate the same way the launch beats do. Strongest single reference for our `editorial_reveal` / stagger presets and for MD-04 gap hunting. | — |
| 7 | **ManvsMachine** — *Apple iMac Pro Artist Film* | Apple / 2018 | Screen-space product film | manvsmachine.co/work/imac-pro [v]; YouTube `suFbHIg-3K0` (remastered 4K upload) [oEmbed] | Grid discipline: everything snaps to screen-space axes; value counters and diagrams frame-enter in monotonic sequence. Source of the `counter_value`/`amountbox` anatomy noted in `REFERENCE_REELS11_ANALYSIS.md`. | — |
| 8 | **ManvsMachine** — *Smirnoff "Live Louder"* | Smirnoff | Broadcast CG | manvsmachine.co/work/smirnoff [v]; YouTube `b7yEC_186ZM` ("LIVE LOUDER with Karol G and Smirnoff", MultiVu) [oEmbed] (*broadcast PR re-upload — treat music/asset rights as unverified; never reuse audio*) | Hard-accented entrances synced to a music pulse; cutting on accent keeps a dense CG film legible. Reinforces our "no dissolve default" hard-cut rhythm and future audio-visual cue checks. | — |
| 9 | **LAD studio** — *Google "Best Phones Forever"* | Google Creative Lab / 2023– | 3D character series | lad.studio/bpf [v] | Long-running series built entirely on two characters and a recurring set — episodic identity beats decorative novelty. When ASTA wants a recurring promo series, system consistency (same render path, same presets) is the differentiator, mirroring our one-engine decision. | — |
| 10 | **State** — *Dell XPS "All The Right Moves"* | Dell / 2026 | Live action + CG overlays | statedesign.tv/work/dell-all-the-right-moves [v] | Graphic overlays (transitions, lower-thirds) match live-action motion direction — the overlay is *motivated by* the plate. Exactly what `render --title-engine studio` must achieve: animation that reads with the underlying footage, not a static card over moving video. Their practice of shipping a multi-format toolkit validates our portrait/square/landscape matrix (MD-03). | — |
| 11 | **Mouthwash** — *Nike After Dark* | Nike | Type/VR-driven title system | mouthwash.studio/work/nike-after-dark [v] | Type as the protagonist with aggressive scale contrast; backgrounds never compete with glyphs. Supports our backdrop `strong`/`soft` opacity tiers (0.68/0.48) and contrast-first QA gating. | — |
| 12 | **Giant Ant** — *Coca-Cola Times Square* | Coca-Cola / 2019– | Looping billboard animation | giantant.ca/coca-cola-case-study [v] (careful: `giantant.com` is a different research-design company) | Infinite-loop composition with no dead frames; designed for watched screens. Reminds us that overlays must respect mid-shot stacking: the library of scenes must start and end meaningfully (logo/CTA behavior) as one loop. | — |
| 13 | **Giant Ant** — *Slack Global Brand Campaign* | Slack / 2019–2020 | Multiformat brand system | giantant.ca/slack-brand-campaign [v] | One grammar (simple shapes, context switches) adapted across 8 languages, print and broadcast. Direct analogue to `format_matrix` and multi-profile assets; text adapted per format without re-designing the system each time. | — |
| 14 | **Giant Ant** — *Nike "Heart of a Legacy"* | Nike / 2020 | Collage motion system | giantant.ca/nike-legacy [v] | Mixed collage depths create perceived camera motion without real focal crops; motivates our `animated_crop` keyframing of focal regions for flat archival imagery. | — |
| 15 | **Ogilvy Group Germany** — *Audi A6 e-tron global launch ("Underestimated", "Seaside", "Design", "Glass Roof")* | Audi / 2024–2025 | Broadcast 360° product campaign | ogilvy.com/de/eng/ideas/ogilvy-enthullt-weltweite-kampagne-fur-den-audi-a6-e-tron [v]; official Vimeo links 1035998379, 1035993371, 1036004306, 1036004363 (on ogilvy.com page) [v] | Feature-by-feature campaign structure: each film sells exactly one product claim with one visual proof-moment. Maps to `deterministic single-claim scene` logic — no four benefits stacked in one scene; prevents invented claims (only verified copy). | — |
| 16 | **Made by Google** — *"Javier in Frame"* Pixel small-business film 2024 | Google / 2024 | Documentary-style commercial | YouTube `wYPTZIFQoDQ` [oEmbed] (Made by Google channel) | Human-first storytelling: real people and one product benefit, captured with lightweight graphic dressing. Orders our ASTA scenes the same way: footage first, overlay restraint (`soft` backdrop or none when the plate carries the message). | — |
| 17 | **LottieFiles** — *Robinhood product motion (case study)* | Robinhood / 2019– | Product/micro-interaction system | lottiefiles.com/case-studies/robinhood [v] | Motion as brand bridge inside product ("screenshotable moments"); animations built from clean shape layers delivered via an animation runtime. Evidence for a future Lottie/dotLottie ingestion path (MD-05): curated component library + documented motion + runtime integration is the industry pattern. | — |
| 18 | **Mailchimp** — *2018 rebrand (Collins)* | Mailchimp / 2018– | Identity/typography system | mailchimp.com/resources/new-brand-announcement-2018/ [v]; design.mailchimp.com [v] | Playful identity held together by strict coarse structure (words + yellow + Coopers). Teaches tolerance: expressive animation on top, conservative typography underneath — our kicker/headline/summary hierarchy must stay boring so the motion can feel alive. | — |

## Distilled design grammar (do not bypass when stylising)

1. **One system, many scenes.** Every frame must be recognisable from `brand.json` tokens
   (palette, typography, kicker style) without a logo present (cf. 1, 4, 13, 18).
2. **Motivated motion.** Overlay animation follows the plate's motion or the beat of the
   copy; nothing floats for decoration (cf. 10, 6).
3. **Enter → hold → exit with purpose.** Minimum readable dwell; entrances are fast,
   exits are fewer and cleaner than entrances (cf. 6, 12). Our presets must always
   guarantee `min_read_frames` before exit.
4. **Grid and axes win.** Counters, metrics and type snap to screen-space axes;
   monotonic build up, never random curves (cf. 7).
5. **One claim per scene.** A single verified benefit + proof moment; stacked claims
   are edited into sequence, not piled into one overlay (cf. 15).
6. **Contrast before decoration.** A darker backdrop beats a prettier but
   unreadable one; glyph contrast is non-negotiable on phone size (cf. 11).
7. **Craft = imperfection with control.** Studio work feels handmade because assets
   are hand-designed, not because effects are sprinkled (cf. 1). Our catalog should
   keep reusing the same imagery thoughtfully rather than inventing decorative
   overlays per scene.
8. **Editorial hierarchy that stays boring.** Kicker / headline / support must remain
   typographically conservative; movement carries the expressiveness (cf. 6, 18).
9. **Series thinking.** Recurring crews, motifs and structures make promos feel
   professional over time; do not re-invent grammar per project (cf. 9, 1, 13).
10. **Every audio-visual accent is checked.** Music pulse ↔ cut/entrance alignment is
    part of QA; silence and right-negatives are owner-verified (cf. 8, 16).

## Explicit negative examples (things this board bans)

These were observed in our own old renders / weak references (see
`docs/REFERENCE_REELS11_ANALYSIS.md`) and are banned going forward:

1. **Pre-burned graphics in "clean" plates.** All 13 ASTA footage clips contain baked-in
   ASTA logos/titles — they are classified `finished_promo` in `asset-reviews.json` and
   are hard-blocked from new overlays. Text baked into records cannot be re-versioned,
   re-cropped, translated, color-managed or QA-gated.
2. **Same entrance effect on every scene.** Constant `pop`/`kinetic_rise` on all 13
   scenes reads as template motion (violates cf. 9: rhythm needs variation, see board
   grammar #3); random variety without system is equally banned.
3. **Decorative SVG/graphics with no data meaning.** Charts and diagrams animate from
   verified data or they do not exist (cf. 7, 15).
4. **Pixel-placed overlays.** Component slots with measured boxes/by-construction
   collision-safe layout; hard-coded cx/cy placement becomes unmaintainable and
   unsupported (cf. grammar #4).
5. **Invented claims/timecodes.** No fabricated data, "taken from customer quotes",
   "tested in X homes", or unverifiable accents (cf. 15; enforced by review flows).
6. **Misrepresented equipment scale** — utility-scale industrial containers shown as
   typical residential battery setups; product visuals must match the advertised
   home-storage context (existing acceptance gate A).
7. **Music/SFX without verified rights.** Including "temp" tracks from any source,
   sidechain pumping artifacts, or clipped peaks; hours of reference work does not
   license its soundtracks for reuse.
8. **Floating transitions.** Dissolves as default; dissolve/dip-to-black only when
   art-directed (existing transition presets contract).
9. **Text everywhere at once.** Overlay must not exceed the reserved safe band; KPI
   badges may not cross the mobile UI cutout (collision/safe-area tests gate this).
10. **Value tricks.** Value counters that start before their scene or overshoot then
    settle down (non-monotonic) are banned; monotonic easing only.

## Before/after benchmark — status and method

Demand: compare the original ~35.55s ASTA reel against the new studio system output
(`renders/asta-energy/asta-motion-system-demo-final.mp4`, 42.0s, silent).

Status: **pending owner material.** The named 35.55s original file was not located in
the repository media tree. Nearest probe: `brands/asta-energy/media/footage/10_tracker-pv.mp4`
(35.392s) — a branded finished-promo clip, useful for shot-by-shape diagnostics of the
old look but **not** a before/after render benchmark.

Method once supplied (no timecodes may be authored without hand-checking both files):
1. Watch both files end-to-end, log nine verified beats (entrance at `mm:ss.f` each).
2. Generate contact sheets + motion strip of both (`storyboard` command).
3. Score against `docs/REVIEW_RUBRIC.md` on phone playback: legibility, dwell,
   claim clarity, brand consistency, rhythm, audio (if licensed mix exists).
4. Record results into `docs/ASTA_CREATIVE_QA.md` with screenshots; owner signs the
   before/after verdict before any default-path migration (MD-02).

## Verification log

- 2026-10-23: all 18 studio/entity-level links fetched HTTP 200 or confirmed via
  YouTube oEmbed title+channel match; timecodes intentionally left blank
  (`—` = must be filled only after manually watching the clip end-to-end).
- Smirnoff entry (8): mirrored YouTube upload is a PR re-upload (MultiVu); used to
  view the work only — rights remain with Smirnoff; **no audio/asset reuse permitted**.
- Airbnb "Surrounded" (1): campaign entry is the umbrella `get-an-airbnb` case page;
  the March 2025 iteration is documented by stashmedia.tv as a secondary source.
- This board intentionally does not host or commit reference media; video bytes stay
  outside the repository.
