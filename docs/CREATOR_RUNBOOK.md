# Creator Runbook (OPS-07)

## Quick Reference: Create a Brand Ad from Start to Finish

```
1. Select brand: reels-maker catalog --brand asta-energy --json
2. Create script: editor/ in brand.json, design a manifest
3. Validate: reels-maker validate <manifest> --root . --strict-quality --json
4. Render: reels-maker render <manifest> --root . --strict-quality --json
5. Inspect: reels-maker storyboard <manifest> --video <mp4> --output <png> --json
6. Approve: record review in docs/REVIEW_RUBRIC.md scorecard
7. Archive: move approved MP4 to renders/<brand>/archive/ with checksum
```

## Step 1: Select a Brand
List all available brands:
```sh
reels-maker catalog --brand asta-energy --json
```
For each video, check `editorial_state` and `overlay_ready`:
- `clean_source` + `overlay_ready: true` → safe for new titles/logos
- `finished_promo` → reuse only, do NOT add new branding
- `unreviewed` → inspect actual frames before reuse

## Step 2: Create a Script and Manifest
Create a project manifest in `brands/<brand>/projects/`. Paths are relative
to the brand directory, not the shell working directory.

Example minimal manifest:
```json
{
  "name": "my-reel",
  "video": {"width": 1080, "height": 1920, "fps": 25},
  "scenes": [
    {
      "file": "media/footage/clean-source.mp4",
      "start": 0,
      "duration": 3.0,
      "title": {"headline": "YOUR HEADLINE"},
      "motion": {"preset": "rise_soft", "duration_frames": 7}
    }
  ],
  "music": {
    "file": "media/audio/background.mp3",
    "start": 0,
    "volume": 0.7,
    "fade_out": 1.0
  },
  "branding": {},
  "output": "renders/asta-energy/my-reel.mp4",
  "brand": "asta-energy"
}
```

## Step 3: Validate the Manifest
```sh
reels-maker validate brands/asta-energy/projects/my-reel.json --root . --strict-quality --json
```
Fix any errors or explain each warning before proceeding.

## Step 4: Render
```sh
reels-maker render brands/asta-energy/projects/my-reel.json --root . --strict-quality --json
```
Verify exit code 0 and a successful JSON response.

## Step 5: Inspect the Output
Generate a contact sheet and motion strip:
```sh
reels-maker storyboard brands/asta-energy/projects/my-reel.json \
  --video renders/asta-energy/my-reel.mp4 \
  --output renders/asta-energy/qa/contact-sheet.png --json

reels-maker storyboard brands/asta-energy/projects/my-reel.json \
  --video renders/asta-energy/my-reel.mp4 \
  --output renders/asta-energy/qa/motion-strip.png \
  --motion-strip --json
```

## Step 6: Human Creative Review
Play the MP4 on a phone with sound. Score each dimension 0-4 using
docs/REVIEW_RUBRIC.md. Any 0/1 blocks approval. Flagship requires all ≥3.
Record the review with:
- Reviewer name and date
- Approved render hash (SHA-256)
- Scores and specific revision list

## Step 7: Archive Approved Media
```sh
mkdir -p renders/asta-energy/archive/
cp renders/asta-energy/my-reel.mp4 renders/asta-energy/archive/
sha256sum renders/asta-energy/my-reel.mp4 > renders/asta-energy/archive/checksums.txt
```

## Key Rules
- Do not overlay new titles/logos on `finished_promo` footage
- Use actual human narration, not synthesized voices
- Verify all source media rights before publication
- Do not render to main branch; work only in refactor/modular-render-engine
- Document any creative exceptions with explicit reasoning

## Tool Versions (CORE-09)
- Python: 3.13.x
- FFmpeg: 8.x
- Dependencies documented in pyproject.toml
- Font fallback: Open Sans -> DejaVu Sans
