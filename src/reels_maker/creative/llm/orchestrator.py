"""Bounded, provider-neutral creative iteration loop.

The model and render/evidence adapters are injected deliberately: this module
never guesses a provider, makes network calls, or claims a mock is a live model.
"""
from __future__ import annotations

import hashlib
import json
import re
import copy
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from ..compiler import _validate_decisions
from ..spec import validate_creative_spec
from .contracts import (
    CreativeContractError,
    validate_art_direction,
    validate_brief,
    validate_concepts,
    validate_scene_program,
    validate_visual_critique,
)
from .revision import apply_scene_revision_patch


class CreativeModel(Protocol):
    def generate_json(self, *, role: str, context: Mapping[str, Any]) -> Any: ...


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _planning_reference_guidance(value: Mapping[str, Any] | None) -> dict:
    """Use caller-matched guidance or retrieve the bundled cited library."""
    if value is None:
        from ..reference_library import load_reference_library
        library = load_reference_library()
        sources = {item["id"]: item for item in library["sources"]}
        recipes = []
        for recipe in library["recipes"]:
            item = copy.deepcopy(recipe)
            item["source_links"] = [
                {"id": source_id, "url": sources[source_id]["url"]}
                for source_id in recipe["reference_ids"]]
            recipes.append(item)
        return {"schema_version": 1, "recipes": recipes,
                "principles": library["principles"],
                "anti_patterns": library["anti_patterns"],
                "note": "Cited craft guidance, not a learned aesthetic score."}
    guidance = copy.deepcopy(dict(value))
    if "recipes" not in guidance and isinstance(guidance.get("recipe"), Mapping):
        recipe = dict(guidance["recipe"])
        recipe["source_links"] = guidance.get("source_links", [])
        guidance["recipes"] = [recipe]
    return guidance


def run_creative_loop(
    brief: dict,
    *,
    model: CreativeModel,
    render_evidence: Callable[[dict, int], Mapping[str, Any]],
    hard_qa: Callable[[dict, dict], Mapping[str, Any]],
    max_rounds: int = 2,
    reference_guidance: Mapping[str, Any] | None = None,
) -> dict:
    """Run concepts -> art direction -> plan -> render -> critique -> revisions.

    ``render_evidence`` must return evidence from the actual renderer and carry
    a stable hash. ``hard_qa`` is authoritative for technical/factual checks.
    Human approval is intentionally not inferred and is always left pending.
    """
    if type(max_rounds) is not int or not 0 <= max_rounds <= 3:
        raise ValueError("max_rounds must be an integer from 0 to 3")
    validated_brief = validate_brief(brief)
    references = _planning_reference_guidance(reference_guidance)
    shared_context = {"brief": validated_brief,
                      "reference_guidance": references}
    concepts = validate_concepts(model.generate_json(
        role="concepts", context=shared_context))
    selection = model.generate_json(role="select_concept", context={
        **shared_context,
        "concepts": concepts,
        "selection_policy": "choose by brief fit and distinct visual storytelling, not preset variety",
    })
    if not isinstance(selection, Mapping) or selection.get("concept_id") not in {
            item["id"] for item in concepts}:
        raise CreativeContractError("selection.concept_id: must refer to a generated concept")
    selected = next(item for item in concepts if item["id"] == selection["concept_id"])
    context = {**shared_context, "selected_concept": selected}
    art_direction = validate_art_direction(model.generate_json(
        role="art_direction", context=context), brief=validated_brief,
        reference_guidance=references)
    scene_order = [scene["id"] for scene in art_direction["scenes"]]
    context["art_direction"] = art_direction
    program = model.generate_json(role="scene_program", context=context)
    program = _validate_program(program, scene_ids=scene_order)
    stable_scene_ids = {shot["id"] for shot in program["creative_spec"]["shots"]}

    ledger: list[dict] = []
    best: dict | None = None
    stop_reason = "round_limit"
    for round_index in range(max_rounds + 1):
        qa = dict(hard_qa(program["creative_spec"], program["decisions"]))
        if qa.get("ok") is not True:
            ledger.append({"round": round_index, "stage": "hard_qa", "result": qa})
            # A model must not be allowed to override factual, rights, or safety
            # failures. Replanning is offered with exact machine findings.
            if round_index >= max_rounds:
                break
            program = _validate_program(model.generate_json(role="repair_hard_qa", context={
                **context, "scene_program": program, "hard_qa": qa,
            }), scene_ids=scene_order)
            continue

        evidence = render_evidence(program, round_index)
        if not isinstance(evidence, Mapping) or not isinstance(evidence.get("sha256"), str):
            raise CreativeContractError("render_evidence: actual render and sha256 are required")
        if not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"]):
            raise CreativeContractError("render_evidence.sha256: expected SHA-256 hex digest")
        critique = validate_visual_critique(model.generate_json(role="critic", context={
            # Deliberately exclude the author's rationale and concept title.
            "brief": validated_brief,
            "evidence": dict(evidence),
        }), evidence_hash=evidence["sha256"])
        unknown_scenes = {issue["scene_id"] for issue in critique["issues"]} - stable_scene_ids
        if unknown_scenes:
            raise CreativeContractError("visual_critique: issue refers to unknown scene id")
        entry = {"round": round_index, "stage": "render_critique",
                 "evidence_sha256": evidence["sha256"],
                 "critique": critique, "hard_qa": qa}
        ledger.append(entry)
        verdict_rank = {"reject": 0, "revise": 1, "accept": 2}[critique["verdict"]]
        candidate = {"program": program, "evidence": dict(evidence), "critique": critique,
                     "hard_qa": qa, "review_status": critique["verdict"]}
        best_rank = ({"reject": 0, "revise": 1, "accept": 2}[best["critique"]["verdict"]]
                     if best is not None else -1)
        if best is None or verdict_rank > best_rank:
            best = candidate
        if critique["verdict"] == "accept":
            stop_reason = "critic_has_no_open_issues"
            break
        if critique["verdict"] == "reject":
            stop_reason = "critic_rejected"
            break
        if round_index >= max_rounds:
            stop_reason = "revision_limit"
            break
        current_hash = _fingerprint(program)
        revision_output = model.generate_json(role="revise", context={
            **context,
            "scene_program": program,
            "critique": critique,
            "immutable_facts": validated_brief["facts"],
            "instruction": "Revise only what the evidence identifies; preserve factual claims and rights.",
        })
        if not isinstance(revision_output, Mapping) or set(revision_output) != {"revision_patch"}:
            raise CreativeContractError(
                "revise: return only a scene-scoped revision_patch, not a replacement program")
        program, patch_report = apply_scene_revision_patch(
            program, revision_output["revision_patch"])
        ledger.append({"round": round_index, "stage": "revision",
                       "patch": patch_report})
        if _fingerprint(program) == current_hash:
            stop_reason = "revision_no_change"
            break

    return {
        "status": "needs_human_review" if best else "blocked_by_hard_qa",
        "selected_concept_id": selected["id"],
        "concepts": concepts,
        "art_direction": art_direction,
        "best_candidate": best,
        "run_ledger": ledger,
        "stop_reason": stop_reason,
        "brief_sha256": _fingerprint(validated_brief),
        "human_approval": "pending",
    }


def _validate_program(value: Any, *, scene_ids: set[str] | None = None) -> dict:
    if not isinstance(value, Mapping):
        raise CreativeContractError("scene_program: expected object")
    spec = value.get("creative_spec")
    try:
        validate_creative_spec(spec)
    except (TypeError, ValueError) as exc:
        raise CreativeContractError(f"scene_program.creative_spec: {exc}") from exc
    ids = scene_ids or {shot["id"] for shot in spec["shots"]}
    program = validate_scene_program(value, scene_ids=ids)
    _validate_decisions(spec, program["decisions"])
    return {"creative_spec": dict(spec),
            "decisions": [dict(item) for item in program["decisions"]]}
