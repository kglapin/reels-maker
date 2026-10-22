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

## Review actual entrance, hold and exit (motion strip)

The default contact sheet samples one **settled** frame per shot. It can miss
bad early entrances, brief opacity problems, or an exit that happens before the
copy is readable. For text-forward ads, also run:

```sh
reels-maker storyboard brands/asta-energy/projects/asta-typography-editorial-demo.json \
  --video renders/asta-energy/asta-typography-editorial-demo.mp4 \
  --output renders/asta-energy/qa/motion-strip.png --motion-strip --json
```

This adds three real decoded frame samples per shot: `entry`, `settled` and
`exit`. The timings avoid incoming/outgoing crossfade intervals. Animated
scene samples prefer the moment after the configured stagger completes for the
settled checkpoint. The command also verifies codec, dimensions, frame count,
FPS and audio before trusting the MP4. Still images are diagnostics, not a
substitute for video playback, rhythm judgement or human creative sign-off.

The motion strip is opt-in because it extracts three times as many images.
