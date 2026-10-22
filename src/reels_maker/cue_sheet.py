"""Deterministic scene and word-cue timing map for narration editors.

Video starts, crossfade overlaps and every spoken-phrase title cue are derived
from the exact same quantized frame plan used by the renderer. This offers
a useful timing contract for voice editing without guessing transcript words.
"""
from __future__ import annotations

from .motion_timing import build_cue_schedule, scripted_text_roles
from .renderer import _frame_counts
from .spec import Project
from .transitions import timeline_frames, transition_plan


def make_cue_sheet(project: Project) -> dict:
    """Return scene-local and global cue positions (integer frames + seconds)."""
    lengths = _frame_counts(project)
    transitions = transition_plan(project, lengths)
    fps = project.fps
    entries = []
    warnings = []
    cursor = 0
    for index, (scene, length) in enumerate(zip(project.scenes, lengths)):
        if index > 0:
            cursor += lengths[index - 1] - transitions[index - 1]["frames"]
        incoming = transitions[index - 1]["frames"] if index else 0
        outgoing = transitions[index]["frames"] if index < len(transitions) else 0
        text_roles = scripted_text_roles(scene.get("title") or {})
        motion = scene.get("motion")
        if motion:
            roles = ["logo", "accent"] + [role for role, _ in text_roles]
            schedule = build_cue_schedule(motion, roles, fps, length)
            offsets = schedule.starts
            fade_frames = schedule.duration_frames
        else:
            offsets = {role: 0 for role, _ in text_roles}
            fade_frames = 0
        scene_cues = []
        for role, message in text_roles:
            local_frame = offsets[role]
            absolute_frame = cursor + local_frame
            settled_frame = absolute_frame + fade_frames
            entry = {
                "role": role,
                "text": message.strip(),
                "local_frame": local_frame,
                "local_seconds": round(local_frame / fps, 5),
                "timeline_frame": absolute_frame,
                "timeline_seconds": round(absolute_frame / fps, 5),
                "settled_frame": settled_frame,
                "settled_seconds": round(settled_frame / fps, 5),
            }
            scene_cues.append(entry)
            if local_frame < incoming:
                warnings.append({
                    "scene": index + 1,
                    "role": role,
                    "code": "cue_begins_inside_crossfade",
                    "message": "Text entrance begins before incoming dissolve is complete"
                })
            if local_frame + fade_frames > length - outgoing:
                warnings.append({
                    "scene": index + 1,
                    "role": role,
                    "code": "cue_ends_inside_outgoing_transition",
                    "message": "Text reveal does not complete before the outgoing overlap"
                })
        entries.append({
            "scene": index + 1,
            "file": scene["file"],
            "start_frame": cursor,
            "start_seconds": round(cursor / fps, 5),
            "length_frames": length,
            "incoming_overlap_frames": incoming,
            "outgoing_overlap_frames": outgoing,
            "cues": scene_cues,
        })
    total = timeline_frames(lengths, transitions)
    voice = project.voiceover or None
    return {
        "name": project.name,
        "fps": fps,
        "total_frames": total,
        "total_seconds": round(total / fps, 5),
        "voiceover": (
            {"source": voice["file"],
             "source_start_seconds": float(voice.get("start", 0)),
             "timeline_offset_seconds": float(voice.get("offset_seconds", 0))}
            if voice else None
        ),
        "scenes": entries,
        "warnings": warnings,
        "manual_audio_review_required": bool(voice),
    }
