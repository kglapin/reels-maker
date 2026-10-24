# F0 audit — Master Plan 2.0

Audit basis: `origin/main` at `eb44810` (2026-10-23), Plan 2.0 in
`docs/MASTER_PLAN.md`, roadmap status, source/tests, GitHub metadata and a
read-only local media inventory. This records evidence and blockers; it is not
creative, legal or owner approval.

## Runtime and code inventory (MD-001)

- The project is a Python 3.11+ package (`pyproject.toml`) with the `reels-maker`
  entry point in `src/reels_maker/cli.py`; local verified environment: Python
  3.13.0, Pillow 11.3.0, FFmpeg/FFprobe 8.0.1.
- Active components include the deterministic FFmpeg render/cache path,
  Pillow-based Studio, Camera Canvas, Creative Spec v1, media search adapters,
  icon rasterizer, asset-library validator, planning, audio QC and storyboard
  QA. `render` and `kinetic-render` retain legacy defaults; Studio integrations
  are opt-in. This is multiple supported paths, not one render graph/runtime.
- Optional extras include PDF/brand tooling, Cairo kinetic rendering and
  CairoSVG icon rendering. Full local unittest run on the unchanged code base:
  269 passed, 1 skipped in 50.309s; the icon raster test skipped because system
  Cairo was not discoverable in this process. Synthetic rendering tests passed.
- Before Plan 2 work, the capability surface was Creative Registry v1 and did
  not describe all providers, license decisions, flags and limits required by
  Registry v2. The new Registry v2 is implemented locally under MD-003.

## Media, rights and provenance (MD-001/004/005)

- `brands/asta-energy/media/footage/` contains 15 ASTA-branded clips. All 15
  have `finished_promo` entries in `asset-reviews.json` and sampled-frame notes
  of baked-in ASTA branding/copy. They are not clean-source overlay inputs.
- A fresh local `reels-maker catalog --brand asta-energy --json` run succeeds
  with 30 catalog items: 15 `finished_promo`, 11 `unreviewed`, 2 `unknown` and
  2 `clean_source`. The two clean-source entries are the separately reviewed
  stock items, not ASTA footage.
- `media/stock/` has 10 WebM files, but only two appear in `asset-library.json`
  with CC0 1.0 source/license metadata. Their review notes still say owner
  sign-off is pending. Eight stock files are not represented in that library.
- Three files in `media/fx/` lack a corresponding source/license/review record.
  Two tracks in `media/audio/` have publication rights unverified. Four
  downloaded Pixabay MP3s are under ignored `imports/audio/` quarantine, not
  approved media. The supplied ASTA logo has no separate rights/approval record.
- Existing library validation requires source/license/resolution/topic/editorial
  state and a human review record, but it is not yet the full Plan 2.0 asset-ID,
  derivative/checksum, platform-rights, expiry/revocation and transform
  provenance contract. No missing rights metadata is inferred here.
- GitHub API reports repository visibility `PUBLIC`; this contradicts the
  private-repository requirement. Do not put confidential/client material or
  new licensed assets in the repo until the owner restores/confirms the policy.

## References and acceptance evidence (MD-002/005)

- `docs/REFERENCE_BOARD.md` contains 18 references and ten design rules, but
  reference timecodes are blank pending actual viewing. Its URL verification
  notes are not a saved run report. It is not the required 24-shot,
  human-annotated golden suite.
- Existing golden-strip and regression tests establish deterministic engine
  behavior only; they do not certify commercial rights, accuracy of claims,
  real-footage quality or human mobile acceptance.
- Historical v1 status claimed 12 clean ASTA footage clips and two clean-source
  flagship outputs. The current media review instead marks all 15 ASTA footage
  clips `finished_promo`; the two CC0 entries are separate stock files. Treat
  the v1 claims as historical, not current acceptance evidence.

## F0 disposition

| Task | Evidence/status |
|---|---|
| MD-001 | Audit evidence recorded above; catalog reproduced; multiple legacy/default and opt-in render paths remain. |
| MD-002 | Partial/blocked: 18 cited references exist; 24 viewed/annotated golden shots still need actual human observation and approval. |
| MD-003 | Implemented locally: public Registry v2 reports the installed photo/video/audio/icon providers and limitations; focused CLI/registry tests pass. |
| MD-004 | Implemented locally: required provider/rights/provenance fields and fail-closed `delivery_ready` gate; unknown rights and unreviewed assets remain blocked; derivative paths are brand-root scoped. Current two CC0 records remain `rights_status: unknown`, so neither is delivery-ready. |
| MD-005 | Reconciled this audit, roadmap and source status; repo is PUBLIC and licensing/human-review gates remain open. |

## Early F1 progress

- **MD-101:** official Pexels/Pixabay photo+video, Unsplash photo, Wikimedia Commons
  image and Openverse image search adapters exist with mock tests. Search results
  are candidates only; one live Wikimedia Commons metadata search verified the
  JSON-first CLI connection (2 results, no downloads). Other providers were not
  called live and no rights were cleared.
- **MD-102 evidence (official provider docs checked 2026-10-23):** Pexels supports
  photo/video API, requires a prominent Pexels link in API use, and documents
  default quotas of 200 requests/hour and 20,000/month. Pixabay's API includes
  image/video endpoints, documents 100 requests/60s per key and requires caching
  search responses for 24h; systematic mass downloads are prohibited and
  permanent image hotlinking is not allowed. These facts are documented at
  [Pexels API](https://www.pexels.com/api/documentation/),
  [Pexels License](https://www.pexels.com/license/),
  [Pixabay API](https://pixabay.com/api/docs/) and
  [Pixabay Content License](https://pixabay.com/service/license-summary/).
- **MD-102/103 implementation:** provider credentials/OAuth checks, local quota
  guards, bounded retries, private persistent search-metadata cache (Pixabay
  24h), exact-item review decisions, deterministic fallback ranking and
  host/IP/redirect/size/timeout-bounded downloads are implemented. Downloads
  only enter brand imports quarantine; synthetic video tests exercised
  FFprobe and explicit H.264/AAC transcode. No API calls or media downloads were
  made; provider results remain rights-unknown absent human decision.
- MD-103 transcode support is limited to an explicitly requested, resource-bounded
  H.264/AAC MP4 derivative (max 120s, 1920px, one FFmpeg thread); original
  format is preserved when no transcode is requested and the container is in the
  safe allowlist. Provider downloads are still unexercised live and approval
  remains `not_approved` in quarantine.
- **MD-105:** an OAuth-backed Openverse audio metadata-only search adapter is
  implemented. Music/SFX files, curated sync licenses, actual mixes and
  playback/legal review are still not supplied or approved.
- A deterministic procedural SFX prototype generates WAV PCM-16 click/whoosh/
  riser/hit samples and writes only to `brands/<slug>/imports/audio/` with a
  recipe/hash sidecar. It remains `rights_status: unknown` and quarantine-only;
  generated output is not automatically approved or safe to publish.
- **DM-001:** local CSV/JSON/XLSX loader requires typed columns, units,
  locale/currency, missing-value policy, authorization provenance and source
  SHA-256. Six synthetic tests exercise the initial version; no external or
  client data was imported. XLSX needs the optional `xlsx` extra.
- **DM-002:** synthetic-only Decimal aggregation/division and calculation ledger
  are implemented; invalid typed values, unauthorized inputs, null aggregates,
  currency mismatch and zero denominators fail closed.
- **DM-003:** chart-family recommendations are planning-only, include rationale,
  alternatives, exact fields/units and missing requirements. Renderer support is
  explicitly `not_assessed`; no chart families are claimed as implemented.
- **MD-203 early QA slice:** Studio samples FreeType per-word ink bounding boxes
  after its existing node/ancestor affine transforms and checks them against the
  layout-safe rectangle. This is not glyph-outline intersection, Camera Canvas
  review, or every-keyframe-extremum coverage. The latest offline-capable suite
  passed (362 run, 356 pass, 6 optional skips for unavailable platform/media
  fixtures); the QA
  remains technical evidence, not a human phone-size approval.
- **MD-104:** pinned Tabler, Phosphor and Material Symbols SVG adapters now use
  the sanitizer/cache, finite non-hallucinatory semantic suggestion map,
  per-pack styles, Material Symbols variants, default brand-logo guards and
  license/source/hash records in Studio export provenance. A temporary synthetic
  1080x1920/30fps render exercised 30 live upstream icons across those three
  packs; 34 icon variants rasterized. The
  contact sheet showed no clipping. The QA tool's expected icon-overload warning
  was from this intentionally dense test grid; this is not a creative sign-off.
  The sanitized metadata report is retained at
  `docs/evidence/md104-icon-pack-smoke.json`. A separate synthetic final-profile
  MP4/storyboard sampled authored rotation at entry/settle/exit. Downloaded
  SVGs and both test MP4s remain outside the repository.

Latest complete local suite after media acquisition and CI test-guard updates:
362 run, 356 passed, 6 skipped in 25.737s; skips guard missing optional Cairo
and LFS-backed media/review fixtures. Existing golden-frame ResourceWarnings and
Pillow deprecation warnings are non-fatal. This is technical evidence only, not
human reference, asset-rights or creative approval.

Safe local work may continue on synthetic fixtures, schemas, providers and
tests. Do not promote quarantined or unknown media, mark human reference reviews
complete, or claim the P0 release gate has passed without its required evidence.
