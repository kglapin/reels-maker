# Editorial Visual Review Rubric (QA-11)

This is a human editorial review rubric, not an AI quality score. For each
delivery, record 0–4 (unacceptable, weak, adequate, good, excellent) from a
human reviewer for the following dimensions, attaching sample frames and
editorial notes.

## Acceptance Policy
- Any dimension scoring 0 or 1 blocks approval.
- Every dimension must score at least 3 for flagship status.
- Scores of 2 require recorded justification and revision.
- Thresholds can be adapted by the owner, but changes must be documented.

## Dimensions

### 1. Hierarchy (0-4)
**Evidence**: The intended hero word/idea is recognized immediately.
- **4**: Hero word dominates within first second; accent color guides the eye
- **3**: Hero word is clear but not immediately dominant
- **2**: Multiple competing focal points; hero word unclear
- **1**: No clear hierarchy; body text competes with headline
- **0**: Unreadable; no discernible information order

### 2. Typography (0-4)
**Evidence**: Consistent baseline, font, kerning, composition and readable body.
- **4**: Consistent typography; no kerning issues; Polish diacritics render correctly
- **3**: Mostly consistent; minor kerning issues; text readable
- **2**: Inconsistent font sizing; some text hard to read
- **1**: Font substitution; broken diacritics; unreadable body copy
- **0**: Font failed to render; text clipped or illegible

### 3. Motion (0-4)
**Evidence**: Easing looks physical and decisive; no bounce, shake or unnecessary FX.
- **4**: Natural ease-out; no velocity jumps, no overshoot, consistent baselines
- **3**: Generally smooth; minor entrance issues
- **2**: Bouncing, shaking, or overshooting elements observed
- **1**: Aggressive random FX (spinning, zooms, glitches)
- **0**: Unwatchable motion; nauseating effects

### 4. Rhythm (0-4)
**Evidence**: Cuts, text entrances and narrator/music accents reinforce the idea.
- **4**: All cues align with audio beats; cuts feel intentional and timed
- **3**: Generally aligned; minor timing inconsistencies
- **2**: Some cues miss beats; rhythm feels arbitrary
- **1**: No synchronization between visuals and audio
- **0**: Conflicting rhythm; visual and audio contradict each other

### 5. Image Treatment (0-4)
**Evidence**: Good crop, exposure, color continuity, no text/object collisions.
- **4**: Subject-focused crop; consistent exposure; no collisions with text
- **3**: Good crop generally; minor exposure shifts; minimal collisions
- **2**: Central crop not subject-aware; visible exposure shifts; minor collisions
- **1**: Poor crop; over-reliance on universal overlays; text overlaps content
- **0**: Severe collisions; text unreadable; distracting color shifts

### 6. Branding (0-4)
**Evidence**: Authentic logo; appropriate clearspace and contrast; no duplicates.
- **4**: Logo authentic; clearspace respected; proper contrast on all backgrounds
- **3**: Logo present; generally good clearspace; minor contrast issues
- **2**: Logo placement suboptimal; some clearspace violations
- **1**: Logo duplicated; baked-in graphics conflict with new overlay
- **0**: Logo missing or incorrect; double-branding on finished promo

### 7. Audio (0-4)
**Evidence**: Speech intelligible, music supportive, balanced transitions.
- **4**: Speech crystal clear; music supportive; no pumping/clipping; AAC onset aligned
- **3**: Speech audible; minor music balance issues; no clipping
- **2**: Speech occasionally obscured; noticeable ducking artifacts
- **1**: Speech frequently unintelligible; music overpowers narration
- **0**: Severe clipping; pumping; speech completely masked

### 8. Narrative (0-4)
**Evidence**: Clear premise, value and credible CTA; correct claims.
- **4**: Compelling story; credible claims; clear CTA with correct contact info
- **3**: Clear story; valid CTA; claims substantiated
- **2**: Story unclear; CTA weak or missing
- **1**: Confusing narrative; questionable claims
- **0**: Misleading claims; false promises; no coherent story

### 9. Platform (0-4)
**Evidence**: UI-safe framing, correct output profile and full mobile legibility.
- **4**: Safe areas respected; correct profile; legible on phone; platform UI overlays checked
- **3**: Generally safe; minor safe-area issues; legible on phone
- **2**: Some content near edges; platform-specific issues possible
- **1**: Content at risky positions; platform UI may obscure key elements
- **0**: Critical content in unsafe areas; output profile wrong

## Review Process
1. Generate contact sheet and motion strip from actual rendered MP4
2. Review at actual smartphone display size (not 4K desktop alone)
3. Play with sound on phone speaker and headphones
4. Spot-check narration word onsets against `voiceover.sync_marks`
5. Record reviewer name, date, and review hash of final MP4
6. Document any revisions before marking complete
