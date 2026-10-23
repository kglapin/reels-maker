# Reference Annotations for ASTA Projects (ART-01/02)

## Visual Style Classification
Three primary styles identified across ASTA project manifests:

### 1. Corporate-Energy (Benefit-Explainer)
- **Projects**: `asta-subsidy-external.json`, `asta-vamos-beat.json`
- **Characteristics**: 
  - Balanced mix of drone, facility, and installation shots
  - Moderate pacing with hard cuts every 2-5 seconds
  - Text hierarchy: kicker → benefit headline → body copy
  - Music: licensed tracks with optional sidechain ducking
  - Typical duration: 15-30s

### 2. Fast Montage (Rush Reel)
- **Projects**: `asta-montage.json`, `asta-rush-demo.json`
- **Characteristics**:
  - Rapid-fire shot selection (1.5-2s per scene)
  - Hard cuts synchronized with music beats
  - Minimal text (kicker + headline only in many scenes)
  - Music: high-energy track driving the pace
  - Typical duration: 20-40s

### 3. Editorial/Typography-Focused
- **Projects**: `asta-typography-editorial-demo.json`, `asta-creative-qa-cut.json`, `asta-creative-qa-dissolve.json`
- **Characteristics**:
  - Longer per-scene dwell time (3-5s)
  - Emphasis on text legibility and hierarchy
  - Optional dissolves between scenes (art-directed)
  - Narration/voiceover sync possible
  - Typical duration: 10-25s

## Annotated Reference: asta-montage.json

### Shot Transition Annotations
- **Default transition**: hard cut (15/15 scenes use cut)
- **Music start**: 10.635s into the reel (note explicit start offset)
- **Music fade**: 1.2s fade-out at end
- **Scene pacing**: 1.98s per scene (consistent throughout)
- **Frame count**: 15 scenes × ~1.98s @ 25fps = ~59 frames per scene

### Text Layer Annotations (per scene)
Each scene has title object with varying hierarchy:
- Some scenes use `headline` as plain text
- Others use `headline` as dict with `runs` array (mixed emphasis, accent color)
- `kicker`, `body`, `footer` vary by scene (some scenes omit certain layers)
- `backdrop`: mostly "soft", some "none"

### Motion Presets
- Most scenes do not specify `motion` preset (defaults apply)
- Some scenes use `editorial_reveal` or `rise_soft` presets
- `stagger_frames`: typically 2 frames at 25fps
- `distance_px`: typically 18px at 1080px reference width

### Audio Annotations
- **Music file**: `media/audio/mewwwwwww-rush-433449.mp3`
- **Start offset**: 10.635s (music begins after initial silent/black period)
- **Volume**: 0.75 (75% of full volume)
- **Fade out**: 1.2s over the last 1.2s of the video

### Visual Content per Scene (brief)
1. Drone aerial shots (establishing context)
2. Facility close-ups (equipment detail)
3. Installation human context (people interacting)
4. Tracker/construction progress
5. Panel/capacity metrics
