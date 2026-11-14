"""Atomic scene-scoped revision patches for Creative Spec + decisions."""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ..compiler import _validate_decisions
from ..spec import CreativeSpecError, validate_creative_spec
from .contracts import (
    CreativeContractError,
    validate_revision_patch,
    validate_scene_program,
)


def apply_scene_revision_patch(program: Mapping[str, Any], patches: Any
                               ) -> tuple[dict, dict]:
    """Apply scene-only JSON patches, then revalidate the entire program.

    The input is never mutated. Scene identity/order, global brief, branding,
    rights and factual source fields are outside the patch surface.
    """
    if not isinstance(program, Mapping):
        raise CreativeContractError("scene_program: expected object")
    original_spec = program.get("creative_spec")
    original_decisions = program.get("decisions")
    if not isinstance(original_spec, Mapping) or not isinstance(original_spec.get("shots"), list):
        raise CreativeContractError("scene_program.creative_spec: expected Creative Spec with shots")
    if not isinstance(original_decisions, list):
        raise CreativeContractError("scene_program.decisions: expected array")
    scene_ids = [str(shot.get("id")) for shot in original_spec["shots"]
                 if isinstance(shot, Mapping)]
    try:
        validate_creative_spec(original_spec)
        _validate_decisions(original_spec, original_decisions)
        validate_scene_program(program, scene_ids=scene_ids)
    except (TypeError, ValueError) as exc:
        raise CreativeContractError(f"scene_program: invalid before revision: {exc}") from exc
    validated_patches = validate_revision_patch(patches, scene_ids=set(scene_ids))
    updated = copy.deepcopy(dict(program))
    applied = []
    for index, patch in enumerate(validated_patches):
        parts = patch["path"].split("/")
        section, scene_id, field = parts[1], parts[2][1:], parts[3]
        collection = (updated["creative_spec"]["shots"] if section == "shots"
                      else updated["decisions"])
        matches = [item for item in collection
                   if isinstance(item, dict) and item.get("id") == scene_id]
        if len(matches) != 1:
            raise CreativeContractError(
                f"revision_patch[{index}].path: scene id must match exactly once")
        target = matches[0]
        exists = field in target
        operation = patch["op"]
        if operation == "replace" and not exists:
            raise CreativeContractError(f"revision_patch[{index}]: replacement target missing")
        if operation in ("add", "replace"):
            if operation == "add" and exists:
                raise CreativeContractError(f"revision_patch[{index}]: addition target exists")
            target[field] = copy.deepcopy(patch["value"])
        else:
            if not exists:
                raise CreativeContractError(f"revision_patch[{index}]: removal target missing")
            del target[field]
        applied.append({"op": operation, "path": patch["path"]})
    try:
        validate_creative_spec(updated["creative_spec"])
        _validate_decisions(updated["creative_spec"], updated["decisions"])
        validate_scene_program(updated, scene_ids=scene_ids)
    except (TypeError, ValueError) as exc:
        raise CreativeContractError(f"revision_patch: result failed validation: {exc}") from exc
    return updated, {"ok": True, "applied": applied,
                     "stable_scene_ids": scene_ids}
