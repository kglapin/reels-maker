"""Small strict JSON contracts for the LLM-led creative workflow.

These validate shape and provenance boundaries; they do not claim that an
idea, critique, or render is aesthetically good.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class CreativeContractError(ValueError):
    """An LLM output failed a versioned creative-workflow contract."""


def _object(value: Any, path: str, required: set[str], optional: set[str] = set()) -> Mapping:
    if not isinstance(value, Mapping):
        raise CreativeContractError(f"{path}: expected object")
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if extra:
            details.append("unknown " + ", ".join(sorted(extra)))
        raise CreativeContractError(f"{path}: " + "; ".join(details))
    return value


def _text(value: Any, path: str, *, max_length: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise CreativeContractError(f"{path}: expected non-empty text (max {max_length})")
    return value.strip()


def _list(value: Any, path: str, *, minimum: int = 1, maximum: int = 24) -> list:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise CreativeContractError(f"{path}: expected {minimum}..{maximum} items")
    return value


def validate_brief(value: Any) -> dict:
    """Validate an immutable creative brief with explicit factual provenance."""
    brief = _object(value, "brief", {"name", "audience", "goal", "promise", "facts",
                                      "brand", "media", "restrictions", "platform"}, {"cta"})
    for key in ("name", "audience", "goal", "promise", "platform"):
        _text(brief[key], f"brief.{key}")
    if brief.get("cta") is not None:
        _text(brief["cta"], "brief.cta")
    facts = _list(brief["facts"], "brief.facts", minimum=0)
    for index, item in enumerate(facts):
        fact = _object(item, f"brief.facts[{index}]", {"id", "claim", "source"})
        for key in ("id", "claim", "source"):
            _text(fact[key], f"brief.facts[{index}].{key}")
    media = brief["media"]
    if not isinstance(media, list):
        raise CreativeContractError("brief.media: expected array")
    for index, item in enumerate(media):
        asset = _object(item, f"brief.media[{index}]", {"id", "path", "rights_status"},
                        {"description"})
        for key in ("id", "path", "rights_status"):
            _text(asset[key], f"brief.media[{index}].{key}")
        if asset["rights_status"] not in ("approved", "unknown", "restricted", "rejected"):
            raise CreativeContractError(f"brief.media[{index}].rights_status: invalid state")
    if not isinstance(brief["brand"], Mapping) or not isinstance(brief["restrictions"], list):
        raise CreativeContractError("brief.brand/restrictions: expected object and array")
    return dict(brief)


def validate_concepts(value: Any) -> list[dict]:
    """Validate distinct strategic ideas, not cosmetic preset variants."""
    concepts = _list(value, "concepts", minimum=2, maximum=5)
    output = []
    ids, mechanisms = set(), set()
    for index, item in enumerate(concepts):
        concept = _object(item, f"concepts[{index}]", {"id", "title", "mechanism",
            "visual_metaphor", "hero_moment", "story_beats", "transition_logic", "risks"})
        for key in ("id", "title", "mechanism", "visual_metaphor", "hero_moment",
                    "transition_logic"):
            _text(concept[key], f"concepts[{index}].{key}")
        if concept["id"] in ids:
            raise CreativeContractError("concepts: duplicate id")
        ids.add(concept["id"])
        mechanism = concept["mechanism"].strip().casefold()
        if mechanism in mechanisms:
            raise CreativeContractError("concepts: concepts must use distinct story mechanisms")
        mechanisms.add(mechanism)
        _list(concept["story_beats"], f"concepts[{index}].story_beats", maximum=12)
        _list(concept["risks"], f"concepts[{index}].risks", minimum=0, maximum=12)
        output.append(dict(concept))
    return output


def validate_art_direction(value: Any, *, brief: Mapping,
                           reference_guidance: Mapping) -> dict:
    """Require an authored film grammar and ordered per-scene visual beats."""
    art = _object(value, "art_direction", {
        "visual_thesis", "hierarchy", "typography", "image_relationship",
        "motion_grammar", "rhythm", "scenes", "risks", "selected_recipe_id",
        "principle_ids", "rejected_anti_patterns",
    })
    for key in ("visual_thesis", "typography", "image_relationship", "rhythm"):
        _text(art[key], f"art_direction.{key}")
    for key in ("hierarchy", "motion_grammar", "risks"):
        items = _list(art[key], f"art_direction.{key}",
                      minimum=0 if key == "risks" else 1, maximum=12)
        for index, item in enumerate(items):
            _text(item, f"art_direction.{key}[{index}]")
    recipes = reference_guidance.get("recipes", [])
    recipe_ids = {item.get("id") for item in recipes if isinstance(item, Mapping)}
    if art["selected_recipe_id"] not in recipe_ids:
        raise CreativeContractError(
            "art_direction.selected_recipe_id: cite a recipe from the retrieved reference library")
    principles = {item.get("id") for item in reference_guidance.get("principles", [])
                  if isinstance(item, Mapping)}
    anti_patterns = {item.get("id") for item in reference_guidance.get("anti_patterns", [])
                     if isinstance(item, Mapping)}
    for key, available in (("principle_ids", principles),
                           ("rejected_anti_patterns", anti_patterns)):
        ids = _list(art[key], f"art_direction.{key}", maximum=12)
        for index, item in enumerate(ids):
            _text(item, f"art_direction.{key}[{index}]", max_length=80)
        if not set(ids).issubset(available):
            raise CreativeContractError(f"art_direction.{key}: cite retrieved library IDs only")
    if not art["principle_ids"] or not art["rejected_anti_patterns"]:
        raise CreativeContractError(
            "art_direction: cite at least one principle and one rejected anti-pattern")
    scenes = _list(art["scenes"], "art_direction.scenes", maximum=24)
    fact_ids = {fact["id"] for fact in brief["facts"]}
    media_ids = {asset["id"] for asset in brief["media"]}
    seen: set[str] = set()
    normalized_scenes = []
    for index, item in enumerate(scenes):
        path = f"art_direction.scenes[{index}]"
        frame = _object(item, path, {
            "id", "viewer_task", "focal_point", "visual_change", "hold",
            "transition_reason", "evidence_ids",
        })
        for key in ("id", "viewer_task", "focal_point", "visual_change",
                    "hold", "transition_reason"):
            _text(frame[key], f"{path}.{key}")
        if frame["id"] in seen:
            raise CreativeContractError("art_direction.scenes: duplicate scene id")
        seen.add(frame["id"])
        evidence_ids = _list(frame["evidence_ids"], f"{path}.evidence_ids",
                             minimum=0, maximum=24)
        for evidence_index, evidence_id in enumerate(evidence_ids):
            _text(evidence_id, f"{path}.evidence_ids[{evidence_index}]")
        unknown = set(evidence_ids) - fact_ids - media_ids
        if unknown:
            raise CreativeContractError(
                f"{path}.evidence_ids: unknown brief evidence id {sorted(unknown)[0]!r}")
        normalized_scenes.append(dict(frame))
    return {**dict(art), "scenes": normalized_scenes}


def validate_scene_program(value: Any, *, scene_ids: set[str] | list[str]) -> dict:
    program = _object(value, "scene_program", {"creative_spec", "decisions"})
    spec = program["creative_spec"]
    decisions = _list(program["decisions"], "scene_program.decisions", maximum=24)
    if not isinstance(spec, Mapping) or not isinstance(spec.get("shots"), list):
        raise CreativeContractError("scene_program.creative_spec: expected Creative Spec v1")
    ids = [str(shot.get("id")) for shot in spec["shots"] if isinstance(shot, Mapping)]
    decision_ids = [str(item.get("id")) for item in decisions if isinstance(item, Mapping)]
    expected = list(scene_ids) if isinstance(scene_ids, list) else None
    valid = (ids == expected and decision_ids == expected if expected is not None else
             set(ids) == scene_ids and set(decision_ids) == scene_ids and
             len(decisions) == len(scene_ids))
    if not valid:
        raise CreativeContractError("scene_program: scene ids must exactly match the brief plan")
    return dict(program)


def validate_visual_critique(value: Any, *, evidence_hash: str) -> dict:
    critique = _object(value, "visual_critique",
                       {"evidence_hash", "verdict", "issues",
                        "observed_modalities"})
    if critique["evidence_hash"] != evidence_hash:
        raise CreativeContractError("visual_critique.evidence_hash: critique refers to other evidence")
    modalities = critique["observed_modalities"]
    if (not isinstance(modalities, list) or not modalities
            or any(item not in ("image", "video", "audio") for item in modalities)
            or not ({"image", "video"} & set(modalities))):
        raise CreativeContractError(
            "visual_critique.observed_modalities: declare image or video evidence actually provided to the model")
    if critique["verdict"] not in ("revise", "accept", "reject"):
        raise CreativeContractError("visual_critique.verdict: choose revise, accept or reject")
    issues = _list(critique["issues"], "visual_critique.issues", minimum=0, maximum=30)
    for index, item in enumerate(issues):
        issue = _object(item, f"visual_critique.issues[{index}]",
                         {"scene_id", "timecode", "observed", "impact", "revision"})
        for key in issue:
            _text(issue[key], f"visual_critique.issues[{index}].{key}")
    if critique["verdict"] == "accept" and issues:
        raise CreativeContractError("visual_critique: accepted result cannot contain unresolved issues")
    return dict(critique)


def validate_revision_patch(value: Any, *, scene_ids: set[str] | None = None) -> list[dict]:
    """Allow only direct, scene-scoped Creative Spec or decision edits."""
    patches = _list(value, "revision_patch", maximum=40)
    spec_fields = {
        "headline", "subtitle", "kicker", "intent", "duration", "asset",
        "assets", "carousel", "layout", "composition", "camera",
        "typography", "transition", "rotation", "value", "visual",
        "icon_library", "icon_assets", "chart", "allow_repeat_reason",
        "split_lines", "cues", "perspective",
    }
    decision_fields = {"layout", "typography_motion", "entrance_presets",
                       "layout_reason"}
    for index, patch in enumerate(patches):
        item = _object(patch, f"revision_patch[{index}]", {"op", "path"}, {"value"})
        if item["op"] not in ("add", "replace", "remove"):
            raise CreativeContractError(f"revision_patch[{index}].op: unsupported")
        path = item["path"]
        if not isinstance(path, str):
            raise CreativeContractError(f"revision_patch[{index}].path: expected JSON pointer")
        parts = path.split("/")
        if (len(parts) != 4 or parts[0] != "" or
                parts[1] not in ("shots", "decisions") or
                not parts[2].startswith("@") or len(parts[2]) == 1):
            raise CreativeContractError(
                f"revision_patch[{index}].path: use /shots/@id/field or /decisions/@id/field")
        scene_id = parts[2][1:]
        if scene_ids is not None and scene_id not in scene_ids:
            raise CreativeContractError(f"revision_patch[{index}].path: unknown scene id")
        allowed_fields = spec_fields if parts[1] == "shots" else decision_fields
        if parts[3] not in allowed_fields:
            raise CreativeContractError(
                f"revision_patch[{index}].path: field is not revision-safe")
        if item["op"] != "remove" and "value" not in item:
            raise CreativeContractError(f"revision_patch[{index}].value: required")
    return [dict(item) for item in patches]
