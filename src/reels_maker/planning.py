"""Brief-to-manifest planning with explainable story roles (MD-07).

The planner converts a human-reviewed brief into a studio manifest draft and
into a machine-readable reasoning report. Two hard rules:

1. **Nothing is invented.** Every headline, metric, checklist item and contact
   field must come verbatim from the brief. Where a scene builder would fall
   back to a template default, this planner refuses and names the missing
   field, because a silent industry-default CTA or number is an invented claim.
2. **Assets are provenance-checked and deterministic.** Only reviewed,
   overlay-ready media enter the plan. Selection order is stable, follows the
   preferred-resolution rotation in `AssetManager.select`, and never repeats a
   file silently: forced reuse is recorded as an explicit warning.

The plan is a *draft*: it still passes through `validate` (studio toolchain:
the draft is a studio manifest, so use `studio-qa` / `studio-render`, not the
legacy file-backed `validate`) and human phone review before any render is
treated as deliverable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .assets.manager import AssetManager, Asset
from .ffmpeg import RenderError

MIN_SCENE_S = 1.2
MAX_SCENE_S = 6.0
PLAN_PROFILE = "review"

ROLE_COMPOSITION = {
    "hook": "statement",
    "context": "spotlight",
    "benefit": "statement",
    "process": "checklist",
    "proof": "amount",
    "stats": "stat-grid",
    "cta": "cta",
}
ROLE_WEIGHT = {
    "hook": .8,
    "context": 1.0,
    "benefit": .9,
    "process": 1.4,
    "proof": 1.2,
    "stats": 1.5,
    "cta": .9,
}
ROLE_REASON = {
    "hook": "Opening beat claims one idea before footage detail appears.",
    "context": "Photography carries context; copy supports the picture.",
    "benefit": "A single spoken-style benefit statement per scene.",
    "process": "Checklist groups concrete steps without stacking claims.",
    "proof": "One verified number gets a dedicated hero-counter scene.",
    "stats": "Four short verified numbers in one comparable grid.",
    "cta": "Contact scene owned by the brief; invented defaults are banned.",
}


class PlanningError(ValueError):
    """The brief is missing reviewed copy, data or eligible media."""


@dataclass
class _Pick:
    scene_index: int
    asset: Asset
    rotation: int
    reason: str
    reused: bool = False


def _text(value, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanningError(
            f"Beat {index + 1} ({field}): reviewed copy is required; the "
            "planner does not invent headlines or body copy.")
    return value.strip()


def _durations(roles: list[str], total: float, fps: int
               ) -> list[float]:
    """Frame-aligned, clamped, exactly summable duration allocation."""
    count = len(roles)
    weights = [ROLE_WEIGHT.get(role, 1.0) for role in roles]
    share_sum = sum(weights)
    durations = [max(MIN_SCENE_S, min(MAX_SCENE_S,
                                      weight / share_sum * total))
                 for weight in weights]
    target = [weight / share_sum * total for weight in weights]
    grid = 1.0 / fps
    for index in range(count):
        durations[index] = round(durations[index] / grid) * grid
    remaining = round(total - sum(durations), 9)
    order = sorted(range(count), key=lambda i: (
        -abs(target[i] - durations[i]), i))
    for _ in range(count * 2):
        if abs(remaining) < 1e-9:
            break
        moved = False
        for index in order:
            ceiling = MAX_SCENE_S if remaining > 0 else MIN_SCENE_S
            headroom = round(ceiling - durations[index], 9)
            if headroom <= 1e-9:
                continue
            delta = math.copysign(min(abs(remaining), headroom), remaining)
            durations[index] = round(durations[index] + delta, 9)
            remaining = round(remaining - delta, 9)
            moved = True
            if abs(remaining) < 1e-9:
                break
        if not moved:
            break
    return durations


class BriefPlanner:
    """Deterministic brief-to-manifest planner owned by a brand scope."""

    def __init__(self, root: str | Path, brand: str):
        self.root = Path(root).resolve()
        self.brand = brand
        self.manager = AssetManager(self.root, brand)
        self.used: set[Path] = set()
        self.rotations: list[int] = []
        self.picks: list[_Pick] = []
        self.warnings: list[dict] = []

    def _pick_asset(self, beat: dict, scene_index: int) -> tuple[str, str]:
        """Return (photo, subject) honoring an explicit reviewed allowlist."""
        assets_config = beat.get("assets") if isinstance(beat, dict) else None
        explicit = (assets_config or {}).get("asset") or beat.get("asset")
        if explicit:
            candidate = next(
                (item for item in self.manager.assets
                 if item.relative == str(explicit)), None)
            if candidate is None:
                raise PlanningError(
                    f"Beat {scene_index + 1}: explicit asset {explicit!r} is "
                    f"not in the reviewed catalog of brand {self.brand!r}.")
            if candidate.editorial_state != "clean_source":
                raise PlanningError(
                    f"Beat {scene_index + 1}: asset {explicit!r} is "
                    f"'{candidate.editorial_state}'; only reviewed clean "
                    "sources may host planner copy. Pass media review first.")
            self.used.add(candidate.path)
            self.picks.append(_Pick(
                scene_index, candidate, 0,
                "Explicitly allowed by the brief and reviewed as clean."))
            return candidate.relative, str(candidate.relative)
        topic = beat.get("topic")
        seed = len(self.rotations)
        try:
            asset = self.manager.select(
                kind="video", topic=topic, exclude=self.used, seed=seed)
        except RenderError as exc:
            raise PlanningError(
                f"Beat {scene_index + 1}: no eligible reviewed media matches "
                f"topic {topic!r}. {exc} Add reviewed media or assign the "
                "beat an explicit allowed asset.") from exc
        self.rotations.append(seed)
        reason = (
            f"Reviewed clean source, topic={topic!r}, rotation step {seed}: "
            "highest-resolution preferred list from the stable asset order.")
        reused = False
        if asset.path in self.used:
            reused = True
            self.warnings.append({
                "code": "asset_reuse",
                "scene_index": scene_index + 1,
                "message": (f"Media pool exhausted; scene {scene_index + 1} "
                            f"reuses {asset.relative}. Visible in the "
                            "report; never silent."),
            })
        self.used.add(asset.path)
        self.picks.append(_Pick(scene_index, asset, seed % 3, reason, reused))
        return asset.relative, str(asset.relative)

    def _scene(self, beat: dict, index: int, duration: float) -> dict:
        role = str(beat.get("role") or "")
        profile = ROLE_COMPOSITION.get(role)
        if profile is None:
            raise PlanningError(
                f"Beat {index + 1}: unknown story role {role!r}; choose from "
                + ", ".join(sorted(ROLE_COMPOSITION)) + ".")
        scene: dict = {"type": profile, "duration": duration}
        if beat.get("kicker"):
            scene["kicker"] = _text(beat["kicker"], "kicker", index)
        headline = _text(beat.get("headline"), "headline", index)
        if beat.get("body"):
            scene["body"] = _text(beat["body"], "body", index)
        if role == "context":
            photo, _ = self._pick_asset(beat, index)
            scene["photo"] = photo
            scene["photo_time"] = float(beat.get("photo_time", .5))
        elif role == "proof":
            value = beat.get("value")
            if isinstance(value, bool) or not value:
                raise PlanningError(
                    f"Beat {index + 1}: the hero counter requires a verified "
                    "'value'; a missing metric is never approximated.")
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as exc:
                    raise PlanningError(
                        f"Beat {index + 1}: 'value' must parse as a number "
                        "for the hero counter.") from exc
            scene["value"] = value
            if beat.get("kicker"):
                scene["kicker"] = _text(beat["kicker"], "kicker", index)
            elif beat.get("counter_label"):
                scene["kicker"] = _text(beat["counter_label"],
                                        "counter_label", index)
            scene["subtitle"] = _text(
                beat.get("subtitle"), "subtitle", index)
            if not beat.get("visual"):
                scene["visual"] = "none"
            if beat.get("format"):
                scene["format"] = beat["format"]
        elif role == "process":
            items = beat.get("items")
            if not isinstance(items, list) or len(items) < 2 or len(items) > 5:
                raise PlanningError(
                    f"Beat {index + 1}: checklist 'items' requires 2–5 "
                    "reviewed, verified strings from the brief.")
            scene["items"] = [
                _text(item, f"items[{position}]", index)
                for position, item in enumerate(items)]
        elif role == "stats":
            stats = beat.get("stats")
            if not isinstance(stats, list) or len(stats) != 4:
                raise PlanningError(
                    f"Beat {index + 1}: stat-grid requires exactly four "
                    "reviewed {label, value} entries from the brief.")
            cleaned = []
            for position, entry in enumerate(stats):
                if not isinstance(entry, dict):
                    raise PlanningError(
                        f"Beat {index + 1}: stat {position + 1} must be an "
                        "object with a label and a verified value.")
                label = _text(entry.get("label"),
                              f"stats[{position}].label", index)
                raw = entry.get("value")
                if isinstance(raw, bool) or raw in (None, ""):
                    raise PlanningError(
                        f"Beat {index + 1}: stat '{label}' has no verified "
                        "value; metric shortcuts are not allowed here.")
                cleaned.append({"label": label, "value": raw,
                                "suffix": entry.get("suffix", ""),
                                "prefix": entry.get("prefix", "")})
            scene["stats"] = cleaned
        elif role == "cta":
            if not beat.get("phone") and not beat.get("website"):
                raise PlanningError(
                    f"Beat {index + 1}: CTA requires the brief's contact "
                    "details (phone or website). The planner never inserts "
                    "placeholder contact claims.")
            if beat.get("phone"):
                scene["phone"] = _text(beat["phone"], "phone", index)
            if beat.get("website"):
                scene["website"] = _text(beat["website"], "website", index)
            scene["line_one"] = _text(beat.get("line_one"), "line_one", index)
            if beat.get("line_two"):
                scene["line_two"] = _text(beat["line_two"], "line_two", index)
            if beat.get("logo"):
                scene["logo"] = beat["logo"]
        return {**scene, "headline": headline}

    def plan(self, brief: dict) -> tuple[dict, dict]:
        """Return (manifest-draft, report). Both are JSON-safe."""
        if not isinstance(brief, dict):
            raise PlanningError("The brief must be a JSON object")
        name = _text(brief.get("name"), "name", -1)
        total = brief.get("duration_s")
        if isinstance(total, bool) or not isinstance(total, (int, float)):
            raise PlanningError("duration_s must be a number of seconds")
        if not 5 <= float(total) <= 90:
            raise PlanningError("duration_s must be between 5 and 90 seconds")
        beats = brief.get("beats")
        if not isinstance(beats, list) or not 3 <= len(beats) <= 8:
            raise PlanningError(
                "beats must be a list of 3–8 reviewed story beats")
        roles = [str(beat.get("role") or "") for beat in beats]
        if roles[0] != "hook":
            raise PlanningError("The first beat must be the hook.")
        if roles[-1] != "cta":
            raise PlanningError("The last beat must be the contact (cta).")
        if roles.count("hook") != 1 or roles.count("cta") != 1:
            raise PlanningError("hook and cta must occur exactly once each.")
        fps = int(brief.get("fps", 30))
        if type(fps) is not int or not 1 <= fps <= 120:
            raise PlanningError("fps must be an integer between 1 and 120")
        durations = _durations(roles, float(total), fps)
        scenes = [self._scene(beat, index, duration)
                  for index, (beat, duration)
                  in enumerate(zip(beats, durations))]
        style = brief.get("style")
        manifest = {
            "name": name,
            "brand": self.brand,
            "export": {"profile": PLAN_PROFILE},
            "scenes": scenes,
        }
        if style:
            manifest["style"] = style
        if brief.get("audio"):
            manifest["audio"] = brief["audio"]
        report = {
            "planner": "brief-v1",
            "deterministic": True,
            "name": name,
            "brand": self.brand,
            "profile": PLAN_PROFILE,
            "duration_requested": total,
            "duration_planned": round(sum(durations), 4),
            "fps": fps,
            "scene_count": len(scenes),
            "roles": [
                {"index": index + 1, "role": role,
                 "composition": ROLE_COMPOSITION[role],
                 "duration": round(durations[index], 3),
                 "reason": ROLE_REASON[role],
                 "copy_source": "brief"}
                for index, role in enumerate(roles)],
            "asset_choices": [
                {"scene_index": pick.scene_index + 1,
                 "file": pick.asset.relative,
                 "editorial_state": pick.asset.editorial_state,
                 "topics": list(pick.asset.topics),
                 "rotation_channel": pick.rotation,
                 "reused": pick.reused,
                 "reason": pick.reason}
                for pick in self.picks],
            "warnings": self.warnings,
            "next_steps": [
                "reels-maker validate the saved manifest with --strict-quality",
                "run studio-qa for collisions, safe areas and contrast",
                "human phone review before any publication-ready render",
            ],
        }
        return manifest, report


def plan_brief(brief: dict, *, root: str | Path, brand: str | None = None
               ) -> tuple[dict, dict]:
    """Convenience wrapper: plan() with a brand slug passed explicitly."""
    brand_slug = brand or (brief or {}).get("brand")
    if not brand_slug or not isinstance(brand_slug, str):
        raise PlanningError(
            "A plan requires a brand slug for asset scoping and licensing.")
    return BriefPlanner(root, brand_slug).plan(brief)


def run_end_to_end_delivery(
    brief: dict,
    *,
    root: str | Path,
    output_mp4: str | Path,
    extra_data_scenes: list[dict] | None = None,
    render: bool = True,
) -> dict:
    """Execute end-to-end brief -> plan -> QA/repair -> MP4 -> provenance ledger (MD-406)."""
    import json
    from .qa.report import audit, repair_scene_layout
    from .renderers.studio import probe_output, render_studio
    from .studio import load_studio

    workspace = Path(root).resolve()
    manifest, plan_report = plan_brief(brief, root=workspace)
    if extra_data_scenes:
        # Insert validated data scenes before the final CTA scene
        manifest["scenes"] = (
            manifest["scenes"][:-1]
            + list(extra_data_scenes)
            + manifest["scenes"][-1:]
        )
    manifest_path = workspace / f"{manifest['name']}-e2e-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    project = load_studio(manifest_path, root=workspace)
    timeline = project.timeline()
    built = project.build(timeline)
    qa_report = audit(project, built, timeline, samples_per_scene=4)
    repairs = []
    if not qa_report["ok"]:
        repaired_scenes = []
        for idx, (raw_scene, loaded_scene, built_item) in enumerate(
            zip(manifest["scenes"], project.scenes, built)
        ):
            rep = repair_scene_layout(built_item.context, loaded_scene, max_retries=2)
            updated_raw = dict(raw_scene)
            for key in ("duration", "composition", "typography_motion"):
                if key in rep["scene"]:
                    updated_raw[key] = rep["scene"][key]
            repaired_scenes.append(updated_raw)
            if rep["repaired"]:
                repairs.append({"scene": idx + 1, "attempts": len(rep["attempts"])})
        manifest["scenes"] = repaired_scenes
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        project = load_studio(manifest_path, root=workspace)
        timeline = project.timeline()
        built = project.build(timeline)
        qa_report = audit(project, built, timeline, samples_per_scene=4)

    render_report = None
    probed = None
    out_path = Path(output_mp4).resolve()
    if render:
        render_report = render_studio(project, output=out_path, supersample=1)
        probed = probe_output(out_path)

    data_provenance = [
        s.get("data_provenance")
        for s in manifest["scenes"]
        if isinstance(s, dict) and s.get("data_provenance")
    ]
    return {
        "schema_version": 1,
        "status": "ok" if qa_report["ok"] else "review",
        "ok": qa_report["ok"] and (not render or render_report["export_quality"]["status"] == "pass"),
        "manifest_path": str(manifest_path),
        "output_mp4": str(out_path) if render else None,
        "plan_report": plan_report,
        "qa_report": qa_report,
        "repairs": repairs,
        "render_report": render_report,
        "probe": probed,
        "provenance_ledger": {
            "asset_choices": plan_report.get("asset_choices", []),
            "data_provenance": data_provenance,
            "human_review_required": True,
        },
    }
