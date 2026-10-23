# Storage and Media Strategy (OPS-02/06/07)

## Repository Structure

```
brands/
├── asta-energy/              # Brand identity, assets, projects
│   ├── BRAND.md              # Editorial guidelines
│   ├── brand.json            # Machine-readable brand config
│   ├── assets/               # Logo (logo.png, logo.svg)
│   ├── media/                # Licensed footage, stock, audio, effects
│   │   ├── footage/          # Original ASTA footage (15 clips)
│   │   ├── stock/            # External stock media (10 WebM clips)
│   │   ├── audio/            # Music tracks and voiceover
│   │   ├── fx/               # Transition overlays
│   │   └── asset-reviews.json # Clean/finished/unreviewed classification
│   ├── projects/             # Project manifests (7+ active)
│   └── references/           # Saved marketing source pages
src/reels_maker/              # Shared engine code (never forked per brand)
docs/                         # Documentation (MASTER_PLAN.md, REFACTOR_PLAN.md, etc.)
tests/                        # Test suite (23+ test files)
renders/                      # Generated outputs (gitignored, not committed)
├── asta-energy/              # Brand-specific renders
│   ├── archive/              # Approved final exports
│   └── qa/                   # Contact sheets, motion strips, QA evidence
.cache/                       # Disposable scene encodes (gitignored)
```

## Git/Git LFS Strategy

### Current State (2026-10-22)
- Repository is **private**, visibility: PRIVATE
- Git tree is approximately 716 MB of file content (primarily media)
- 10 external stock media entries tracked via Git LFS pointers
- 8 historical MP4 reference exports kept for regression evidence
- Historical intermediates preserved under archives/ for audit

### Policy
- Do NOT force-push or rewrite Git history
- Large media files (>=50MB) SHOULD use Git LFS when first added
- Git LFS pointers in the tree require `git lfs pull` to hydrate
- Pre-commit hooks prevent accidental addition of unsupported media
- `.gitignore` excludes:
  - `renders/` — generated outputs
  - `.cache/` — scene cache
  - `__pycache__/` — Python bytecode
  - `*.pyc`, `*.pyo` — compiled Python

## Artifact Provenance (OPS-06)

Each render includes provenance metadata in the output JSON:
- **commit_sha**: Git commit hash of the engine code
- **source_checksums**: SHA-256 checksums of all source files
- **brand_revision**: Version hash of brand.json used
- **audio_mix_settings**: Music start, volume, fade_out, ducking mode
- **approved_profile**: Video dimensions, FPS, codec profile
- **render_time**: Total render duration in seconds
- **toolchain**: Python version, FFmpeg version, codec

## Durable Storage Recommendation

### Raw Footage, Stock, Music
- **Primary**: Git LFS pointers in repository (currently in use)
- **Secondary**: Encrypted private object store backup for disaster recovery
- **Access**: Owner-approved collaborators via GitHub

### Generated Exports
- **Approved**: `renders/<brand>/archive/` with SHA-256 checksums
- **Working**: `renders/<brand>/` (gitignored, ephemeral)
- **QA evidence**: `renders/<brand>/qa/` contact sheets and motion strips
- **Private delivery**: Short retention (14 days) for CI artifacts

### Recovery Path
1. Clone repository: `git clone <repo-url>`
2. Pull LFS: `git lfs pull`
3. Install Python deps: `pip install -e '.[pdf]'`
4. Render: `reels-maker render <manifest> --root . --json`
5. Verify: `reels-maker validate <manifest> --root . --json`

## Private Access Control

- Repository visibility: PRIVATE
- Collaborators: Owner (kglapin) only
- GitHub Apps: None (no third-party integrations)
- Deploy keys: Not used
- Branch protection: Requires PR review before merge
- Artifact retention: 14 days (short, private)
