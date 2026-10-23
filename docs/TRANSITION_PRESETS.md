# Transition Presets (EDIT-03/04/05/06)

## Three Pace Classes for Transition Selection

### 1. Slow Pace — Contemplative (0.55–1.1s / 14–30 frames at 25fps)
**Use case**: Static establishment shots, installation wide angles, reflective moments
**Suitable footage**: Drone establishing shots, wide facility views, people walking into frame
**Transition types**:
- **Dissolve**: 24 frames (0.96s) — gentle fade between compositions
- **Dip-to-black**: 20 frames (0.8s) — black screen pause before next composition
- **Cut**: instantaneous, no overlap

### 2. Medium Pace — Standard B2B (0.35–0.55s / 9–14 frames at 25fps)
**Use case**: Typical installation footage, tracker progression, saw operation sequences
**Suitable footage**: Panel installations, tracker movement, blade/saw operations, facility close-ups
**Transition types**:
- **Cut**: default, hard cut between shots
- **Dissolve**: 16 frames (0.64s) — moderate transition density
- **Motivated wipe**: lateral direction matching subject movement (e.g., left-to-right wipe for rightward motion)

### 3. Fast Pace — Energetic/Rhythmic (0.2–0.35s / 5–9 frames at 25fps)
**Use case**: Drone dynamic sequences, beat-synchronized montage, rapid clip progression
**Suitable footage**: Drone aerials, walking persons, beat-driven montage
**Transition types**:
- **Cut**: default, rhythmic hard cuts
- **Dissolve**: 12 frames (0.48s) — faster dissolve for energetic pace
- **Motion wipe**: 8-12 frames, direction motivated by subject movement

## Transition Duration Rules (EDIT-04)

### Core Rule
- Opt-in transitions must not exceed 0.35s (350ms) per EDIT-04
- `max(frames) <= max(2, int(fps * .35))` — already enforced in spec.py validation
- Transition frames must be >= 2 frames (minimum visible change)

### Pace-Class Mapping (at 25 FPS)
| Pace Class | Max Duration | Max Frames | Typical Use |
|------------|-------------|------------|-------------|
| Slow | 1.0s | 25 | Contemplative opens/closes |
| Medium | 0.5s | 13 | Standard B2B flow |
| Fast | 0.35s | 9 | Energetic montage cuts |

### Overlap Warning (EDIT-02)
- Dissolve outgoing overlap reduces effective reading window
- strict-quality lint accounts for overlap: `reading_window = scene_duration - overlap_frames / fps`
- If reading window < 0.55s, warning issued before encode

## Transition Preview Matrix (EDIT-05)

### Build from Real Clean Footage
For each shot pair in a montage, evaluate:

| Shot A Type | Shot B Type | Recommended Transition | Rationale |
|-------------|-------------|-----------------------|-----------|
| Drone (aerial) | Drone (aerial) | Cut or short dissolve (12f) | Matching perspective; dissolve for smooth flow |
| Drone | Installation (ground) | Cut | Perspective change is abrupt; cut locks the change |
| Installation (wide) | Installation (close) | Dissolve (16f) | Gradual focus change; maintains visual continuity |
| Installation (close) | Same type (different angle) | Cut or motivated wipe | Maintains subject continuity |
| Saw/Blade (action) | Saw/Blade (action) | Cut (rhythmic) | Beat-synchronized, maintains energy |
| Walking/Person | Walking/Person | Cut or short dissolve (8f) | Maintains rhythm; dissolve for scene rhythm |
| Static Panel | Any | Cut | Static subjects benefit from clean cuts |

### J-Cut / L-Cut Support
- **J-cut**: Outgoing audio continues into incoming scene (before visual change)
- **L-cut**: Outgoing visual continues into incoming scene (audio change first)
- Both require narrator/music track with explicit audio separation (voiceover + music tracks)
- Not applicable for music-only montages without voiceover

## Quality Checks (EDIT-06)

### xfade Compatibility Verification
- Verify first/last frame behavior: no black flash at transition start/end
- VFR (Variable Frame Rate) resampling: ensure consistent frame counting
- Abrupt luminance shifts: measure delta between outgoing last frame and incoming first frame
- Double-encoding quality: avoid re-encoding unchanged segments; use stream-copy where possible

### Black Frame Detection
- Detect if transition produces unintended black frames at boundaries
- Flag if incoming scene starts with black/low-brightness and outgoing ends dark

### Luminance Shift Measurement
- Compute mean luminance difference between:
  - Last frame of outgoing scene (after any fade-out)
  - First frame of incoming scene (after any fade-in)
- Flag if delta > 0.3 (on 0-1 scale) without artistic intent

### FFmpeg xfade Validation
- Test with `ffmpeg -vf "xfade=prev_next:duration=N"` 
- Verify output seeks correctly, no corrupt frames at boundaries
- Check AAC mux synchronization after xfade assembly
