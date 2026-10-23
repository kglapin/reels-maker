# Flagship Delivery Bundle (REL-02 through REL-14)

## Two Approved Reel Variants

### 1. Editorial Benefit Explainer (variant 1)
- **Manifest**: `brands/asta-energy/projects/asta-flagship-01-editorial.json`
- **Output**: `renders/asta-energy/flagship-editorial-benefit.mp4`
- **Style**: Considered B2B benefit explainer
- **Duration**: 18.0s (17.68s actual)
- **Footage**: 5 clean_source clips (drone, tracker, installation, facility)
- **Audio**: Licensed music track with background volume
- **Quality**: Pass (0 warnings)
- **SHA-256**: 3de488405d243c3f...

### 2. Fast Case Study Montage (variant 2)
- **Manifest**: `brands/asta-energy/projects/asta-flagship-02-montage.json`
- **Output**: `renders/asta-energy/flagship-fast-montage.mp4`
- **Style**: Fast-paced case study montage
- **Duration**: 27.7s (27.72s actual)
- **Footage**: 14 clean_source clips (drone, tracker, saw, installation)
- **Audio**: Licensed music track with beat-sync rhythm
- **Quality**: Pass (0 warnings)
- **SHA-256**: df3919e0b128c06d...

## Creative Briefs (REL-02)

### Variant 1: Editorial Benefit
- **Audience**: Commercial property owners seeking solar investment
- **Offer**: Professional solar installations for businesses
- **Factual claims**: 30% energy cost reduction (typical range)
- **CTA**: Contact via asta-energy.pl
- **Placement profile**: 1080x1920 portrait for social media

### Variant 2: Fast Montage
- **Audience**: Prospective B2B customers browsing social feeds
- **Offer**: Solar installations across diverse property types
- **Factual claims**: 156 panels per standard installation, 39.96 kWp capacity
- **CTA**: Implicit trust via diverse installation showcase
- **Placement profile**: 1080x1920 portrait for social media

## Reproducible Delivery Commands

```sh
# Render variant 1
reels-maker render brands/asta-energy/projects/asta-flagship-01-editorial.json --root . --strict-quality --json

# Render variant 2
reels-maker render brands/asta-energy/projects/asta-flagship-02-montage.json --root . --strict-quality --json

# Validate before render
reels-maker validate brands/asta-energy/projects/asta-flagship-01-editorial.json --root . --strict-quality --json
reels-maker validate brands/asta-energy/projects/asta-flagship-02-montage.json --root . --strict-quality --json

# Generate contact sheets and motion strips
reels-maker storyboard brands/asta-energy/projects/asta-flagship-01-editorial.json --video renders/asta-energy/flagship-editorial-benefit.mp4 --output renders/asta-energy/qa/flagship-editorial-contact-sheet.png --json
reels-maker storyboard brands/asta-energy/projects/asta-flagship-02-montage.json --video renders/asta-energy/flagship-fast-montage.mp4 --output renders/asta-energy/qa/flagship-montage-contact-sheet.png --json
```

## Review Records (REL-10)

Each deliverable has:
- Provenance JSON (commit SHA, checksums, profile, timings)
- Contact sheet (one settled frame per scene)
- Motion strip (entry/settled/exit frames per scene)
- Strict-quality validation report

## Approval Status
- Both variants pass automated QA (export quality, format checks)
- Both use 100% clean_source footage (no baked-in logos/captions)
- Both pass strict-quality mode (0 warnings)
- Human creative review: PENDING (requires phone-size playback and headphone listening)
