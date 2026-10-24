"""Narration cue planning from real word timestamps.

The engine never guesses word onsets from raw audio. A transcript with measured
timestamps is required; without one, manifests keep their explicit cue times
and the QA report states that no automatic audio-text guarantee exists.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

WORD_SPLIT = re.compile(r"\s+")
PUNCT = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)


def _clean(text: str) -> str:
    return PUNCT.sub("", text).lower()


@dataclass(frozen=True)
class WordCue:
    text: str
    start: float
    end: float
    index: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("Word cues require 0 <= start <= end")


@dataclass(frozen=True)
class PhraseCue:
    phrase: str
    start: float
    end: float
    words: tuple[int, ...]


@dataclass
class CuePlan:
    scenes: dict[int, dict[str, float]]
    warnings: list[dict]
    source: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "scenes": {str(index + 1): values
                       for index, values in sorted(self.scenes.items())},
            "warnings": list(self.warnings),
        }


def load_transcript(path: str | Path) -> list[WordCue]:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Transcript does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "words" not in data:
                raise ValueError(
                    "Transcript JSON requires word-level `words`; segment "
                    "timestamps are not precise enough for automatic sync")
            data = data["words"]
        words = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError("Transcript JSON must contain word objects")
            text = item.get("word", item.get("text"))
            start = item.get("start")
            end = item.get("end", start)
            if text is None or start is None:
                raise ValueError("Transcript words require text and start")
            words.append(WordCue(str(text), float(start), float(end), index))
        return words
    if suffix in (".srt", ".vtt"):
        return _parse_subtitles(path.read_text(encoding="utf-8"))
    raise ValueError("Transcript must be .json, .srt or .vtt")


def _parse_subtitles(text: str) -> list[WordCue]:
    """Retain subtitle cue start/end without inventing intra-cue word times."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    words: list[WordCue] = []
    index = 0
    position = 0
    time_pattern = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")

    def seconds(hours, minutes, secs, millis):
        return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(millis) / 1000

    while position < len(lines):
        line = lines[position].strip()
        match = time_pattern.search(line)
        if not match:
            position += 1
            continue
        start = seconds(*match.groups()[:4])
        end = seconds(*match.groups()[4:])
        position += 1
        caption = []
        while position < len(lines) and lines[position].strip():
            caption.append(lines[position].strip())
            position += 1
        tokens = [token for token in WORD_SPLIT.split(" ".join(caption))
                  if token]
        # These words share the measured subtitle cue bounds. They can locate
        # a caption-level phrase, but do not imply individual spoken word
        # onsets; callers must preserve that limitation in the QA report.
        for token in tokens:
            words.append(WordCue(token, round(start, 4), round(end, 4), index))
            index += 1
    return words


def find_phrase(words: Iterable[WordCue], phrase: str) -> PhraseCue | None:
    words = list(words)
    target = [_clean(part) for part in WORD_SPLIT.split(phrase) if _clean(part)]
    if not target:
        return None
    cleaned = [_clean(word.text) for word in words]
    for start in range(0, len(words) - len(target) + 1):
        if cleaned[start:start + len(target)] == target:
            end_index = start + len(target) - 1
            return PhraseCue(phrase, words[start].start, words[end_index].end,
                             tuple(range(start, end_index + 1)))
    return None


def plan_cues(scenes: list[dict], words: list[WordCue],
              *, source: str = "word-timestamps") -> CuePlan:
    """Map each scene's ``cue_phrases`` to measured narration onsets."""
    if not words:
        raise ValueError("Cue planning requires timestamped words")
    result: dict[int, dict[str, float]] = {}
    warnings: list[dict] = []
    if source == "subtitle-cue":
        warnings.append({
            "code": "caption_level_sync",
            "message": ("Subtitle cue boundaries are approximate phrase cues, "
                        "not manually verified word onsets."),
        })
    for index, scene in enumerate(scenes):
        phrases = scene.get("cue_phrases")
        if not phrases:
            continue
        if not isinstance(phrases, dict):
            raise ValueError("cue_phrases must be an object of role: phrase")
        cues: dict[str, float] = {}
        for role, phrase in phrases.items():
            found = find_phrase(words, str(phrase))
            if found is None:
                warnings.append({
                    "code": "phrase_not_found",
                    "scene": index + 1,
                    "role": role,
                    "phrase": str(phrase),
                    "message": ("Narration phrase was not found; the scene keeps "
                                "its manifest cue or automatic stagger."),
                })
                continue
            cues[role] = round(found.start, 4)
        if cues:
            result[index] = cues
    return CuePlan(result, warnings, source)


def apply_cue_plan(scenes: list[dict], plan: CuePlan) -> list[dict]:
    """Merge narration cues without overwriting explicit editor decisions."""
    merged = []
    for index, scene in enumerate(scenes):
        scene = dict(scene)
        if index in plan.scenes:
            existing = dict(scene.get("cues") or {})
            for role, value in plan.scenes[index].items():
                existing.setdefault(role, value)
            scene["cues"] = existing
            scene["cue_source"] = "narration"
        merged.append(scene)
    return merged


def sfx_plan(scene_lengths: list[float], cues: Mapping[int, Mapping[str, float]],
             *, style: str = "kinetic-advertising") -> list[dict]:
    """Propose a restrained sound-design layer, not a wall of effects."""
    events = []
    cursor = 0.0
    for index, length in enumerate(scene_lengths):
        if index:
            events.append({"kind": "transition", "scene": index + 1,
                           "time": round(cursor, 4),
                           "asset": "whoosh-soft" if style != "editorial-premium"
                           else "air-soft", "gain_db": -19})
        scene_cues = cues.get(index, {})
        for role, seconds in scene_cues.items():
            if role in ("amount", "total", "value", "percent"):
                events.append({"kind": "counter", "scene": index + 1,
                               "time": round(cursor + float(seconds), 4),
                               "asset": "tick-soft", "gain_db": -24})
        cursor += length
    return events


def select_compatible_audio(
    candidates: Iterable[Mapping[str, object]],
    *,
    platform: str,
    required_duration: float,
    kind: str = "music",
    require_reviewed_rights: bool = True,
) -> dict:
    """Filter and rank legal cross-platform audio candidates fail-closed (MD-401)."""
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("platform must be a non-empty string")
    if required_duration <= 0:
        raise ValueError("required_duration must be positive")
    if kind not in ("music", "sfx"):
        raise ValueError("kind must be music or sfx")
    target_platform = platform.strip().lower()
    eligible = []
    rejected = []
    for idx, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            raise ValueError(f"audio candidate {idx} must be a mapping")
        cid = str(item.get("id") or item.get("file") or f"audio-{idx}")
        item_kind = str(item.get("kind", "music")).lower()
        if item_kind != kind:
            rejected.append({"id": cid, "reason": f"kind_mismatch:{item_kind}"})
            continue
        rights = str(item.get("rights_status", "unknown")).lower()
        delivery_ready = bool(item.get("delivery_ready", False))
        if require_reviewed_rights and (rights != "approved" or not delivery_ready):
            rejected.append({"id": cid, "reason": "unreviewed_or_unapproved_rights"})
            continue
        platforms = [str(p).lower() for p in (item.get("platforms_allowed") or [])]
        if target_platform not in platforms and "all" not in platforms:
            rejected.append({"id": cid, "reason": f"platform_not_allowed:{target_platform}"})
            continue
        duration = float(item.get("duration") or 0.0)
        loopable = bool(item.get("loopable", False))
        if kind == "music" and duration < required_duration and not loopable:
            rejected.append({"id": cid, "reason": "duration_too_short"})
            continue
        duration_delta = abs(duration - required_duration)
        score = round(1.0 / (1.0 + duration_delta / max(1.0, required_duration)), 6)
        eligible.append({
            "id": cid,
            "file": item.get("file"),
            "duration": duration,
            "license": item.get("license"),
            "score": score,
        })
    eligible.sort(key=lambda r: (-r["score"], r["id"]))
    selected = eligible[0] if eligible else None
    return {
        "ok": selected is not None,
        "selected": selected,
        "eligible": eligible,
        "rejected": rejected,
    }
