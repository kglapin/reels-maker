# Visual QC storyboard for motion designers

Text-heavy video cannot be certified by a JSON schema or aesthetic heuristics.
Use real rendered pixels at actual edit points. A contact sheet is a fast first
review of hierarchy, shot variety, crop, logo use, safe zones and contrast.

```sh
reels-maker render brands/asta-energy/projects/asta-typography-editorial-demo.json --json
reels-maker storyboard brands/asta-energy/projects/asta-typography-editorial-demo.json \
  --video renders/asta-energy/asta-typography-editorial-demo.mp4 \
  --output renders/asta-energy/qa/typography-contact-sheet.png --json
```

The contact sheet samples one clean frame from each scene, avoiding overlap
transitions. It validates MP4 output size and duration against the project and
stops if the MP4 is stale or incompatible. No new stock graphics or motion
presets are invented.

Inspect at normal smartphone size, preferably with muted sound first. Review:
- Dominant word reads first; hierarchy remains obvious without audio
- Logo is authentic, correctly positioned and clear of interface controls
- Text does not clip or cover faces, equipment, or important shot details
- Saturation and color are consistent across scenes; no unnecessary FX
- Shots have enough time to read, and contact-sheet cuts look intentional
- Final MP4 must also be played in motion with audio, not judged from stills

This tool is a **visual review aid**, not an automatic creative approval.
