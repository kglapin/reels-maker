"""Typed, additive Creative Intent -> Motion Plan -> Render Graph boundary.

This boundary deliberately adapts to the existing Studio manifest contract; it
does not introduce a renderer or change the v1 compiler/CLI defaults. Stage
snapshots are JSON-backed so callers cannot mutate an upstream stage by
retaining references to input dictionaries.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from .compiler import compile_creative_spec
from .director import plan_shots
from .spec import CreativeSpecError, validate_creative_spec


def _canonical(value: Any, path: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CreativeSpecError(path, "must contain JSON-compatible values") from exc


def _decode(value: str) -> Any:
    return json.loads(value)


@dataclass(frozen=True)
class CreativeIntent:
    """A validated, immutable snapshot of Creative Spec v1 input."""

    _spec_json: str
    fingerprint: str

    def __post_init__(self) -> None:
        data = _decode(self._spec_json)
        validate_creative_spec(data)
        expected = hashlib.sha256(self._spec_json.encode("utf-8")).hexdigest()
        if self.fingerprint != expected:
            raise CreativeSpecError("$", "intent fingerprint does not match snapshot")

    @property
    def name(self) -> str:
        return _decode(self._spec_json)["name"]

    @property
    def mode(self) -> str:
        return validate_creative_spec(_decode(self._spec_json))["mode"]

    @property
    def spec(self) -> dict:
        """Return a defensive copy of the validated v1 input."""
        return _decode(self._spec_json)


@dataclass(frozen=True)
class MotionDecision:
    """A renderer-capability-checked per-shot Director decision."""

    scene_id: str
    layout: str
    typography_motion: str
    _decision_json: str

    def __post_init__(self) -> None:
        data = _decode(self._decision_json)
        if (data.get("id") != self.scene_id or data.get("layout") != self.layout
                or data.get("typography_motion") != self.typography_motion):
            raise CreativeSpecError("$.motion_plan", "typed decision fields do not match payload")

    @property
    def decision(self) -> dict:
        return _decode(self._decision_json)


@dataclass(frozen=True)
class MotionPlan:
    """Deterministic, intent-bound output of the existing heuristic Director."""

    intent_fingerprint: str
    decisions: tuple[MotionDecision, ...]
    _intent_json: str

    def __post_init__(self) -> None:
        intent = CreativeIntent(self._intent_json, self.intent_fingerprint)
        expected = plan_shots(intent.spec)
        actual = [decision.decision for decision in self.decisions]
        if actual != expected:
            raise CreativeSpecError("$.motion_plan", "decisions do not match validated intent")


@dataclass(frozen=True)
class RenderScene:
    """One timed, legacy-renderer scene payload in the common graph boundary."""

    scene_id: str
    start: float
    duration: float
    _payload_json: str

    def __post_init__(self) -> None:
        if (not self.scene_id or not math.isfinite(self.start)
                or not math.isfinite(self.duration) or self.start < 0
                or self.duration <= 0 or not isinstance(_decode(self._payload_json), dict)):
            raise CreativeSpecError("$.render_graph.scenes", "invalid timed scene node")

    @property
    def payload(self) -> dict:
        return _decode(self._payload_json)


@dataclass(frozen=True)
class RenderGraph:
    """Typed timeline adapter for an existing renderer input.

    ``backend`` identifies an existing contract, not a shared rendering
    implementation: Studio and Camera Canvas remain separate renderer paths.
    """

    backend: str
    width: int
    height: int
    fps: int
    scenes: tuple[RenderScene, ...]
    _manifest_json: str
    _report_json: str

    def __post_init__(self) -> None:
        if self.backend not in ("studio_manifest_v1", "camera_canvas_manifest_v1"):
            raise CreativeSpecError("$.render_graph.backend", "unsupported renderer capability")
        if any(type(value) is not int for value in (self.width, self.height, self.fps)):
            raise CreativeSpecError("$.render_graph.video", "dimensions and fps must be integers")
        if not (180 <= self.width <= 4096 and 180 <= self.height <= 4096
                and 1 <= self.fps <= 120):
            raise CreativeSpecError("$.render_graph.video", "unsupported output dimensions or fps")
        manifest = _decode(self._manifest_json)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("scenes"), list):
            raise CreativeSpecError("$.render_graph", "manifest requires a scenes array")
        if len(manifest["scenes"]) != len(self.scenes):
            raise CreativeSpecError("$.render_graph.scenes", "scene count differs from manifest")
        expected_start = 0.0
        ids = set()
        for index, scene in enumerate(self.scenes):
            if scene.scene_id in ids or not math.isclose(scene.start, expected_start,
                                                          abs_tol=1e-8):
                raise CreativeSpecError("$.render_graph.scenes", "scene ids/timing are ambiguous")
            ids.add(scene.scene_id)
            if (manifest["scenes"][index].get("id") != scene.scene_id
                    or float(manifest["scenes"][index].get("duration", -1)) != scene.duration
                    or scene.payload != manifest["scenes"][index]):
                raise CreativeSpecError("$.render_graph.scenes", "typed scene differs from manifest")
            expected_start = round(expected_start + scene.duration, 9)
        if (manifest.get("schema_version") != 1
                or manifest.get("video") != {"width": self.width, "height": self.height,
                                              "fps": self.fps}):
            raise CreativeSpecError("$.render_graph", "manifest does not match typed graph")
        report = _decode(self._report_json)
        expected_backend = f"{report.get('mode')}_manifest_v1"
        if report.get("ok") is not True or self.backend != expected_backend:
            raise CreativeSpecError("$.render_graph.report", "expected successful compile report")

    def to_renderer_input(self) -> dict:
        """Return the exact Studio manifest produced by the v1 compiler."""
        return _decode(self._manifest_json)

    @property
    def report(self) -> dict:
        return _decode(self._report_json)


def creative_intent(spec: dict) -> CreativeIntent:
    """Validate and snapshot a Creative Spec v1 document."""
    validate_creative_spec(spec)
    encoded = _canonical(spec, "$")
    return CreativeIntent(encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest())


def plan_motion(intent: CreativeIntent) -> MotionPlan:
    """Plan using only the deterministic, currently supported Director."""
    if not isinstance(intent, CreativeIntent):
        raise TypeError("plan_motion requires a validated CreativeIntent")
    decisions = tuple(
        MotionDecision(item["id"], item["layout"], item["typography_motion"],
                       _canonical(item, "$.motion_plan"))
        for item in plan_shots(intent.spec)
    )
    return MotionPlan(intent.fingerprint, decisions, intent._spec_json)


def render_graph(intent: CreativeIntent, motion_plan: MotionPlan, *,
                 source_dir: str = ".", root: str | None = None,
                 check_assets: bool = True) -> RenderGraph:
    """Convert typed stages into the existing, validated renderer contract.

    Unsupported/ambiguous render capabilities fail in the v1 validator and
    compiler. No new node kinds, transforms, media, or renderer defaults are
    inferred here.
    """
    if not isinstance(intent, CreativeIntent) or not isinstance(motion_plan, MotionPlan):
        raise TypeError("render_graph requires CreativeIntent and MotionPlan stages")
    if motion_plan.intent_fingerprint != intent.fingerprint:
        raise CreativeSpecError("$.motion_plan", "plan was derived from a different intent")
    if motion_plan._intent_json != intent._spec_json:
        raise CreativeSpecError("$.motion_plan", "plan intent snapshot mismatch")
    manifest, report = compile_creative_spec(
        intent.spec, source_dir=source_dir, root=root, check_assets=check_assets)
    expected = [decision.decision for decision in motion_plan.decisions]
    actual = plan_shots(intent.spec)
    if expected != actual:
        raise CreativeSpecError("$.motion_plan", "unsupported or inconsistent motion decisions")
    width, height, fps = (manifest["video"][key] for key in ("width", "height", "fps"))
    scenes = []
    start = 0.0
    for item in manifest["scenes"]:
        duration = float(item["duration"])
        scenes.append(RenderScene(item["id"], start, duration,
                                  _canonical(item, "$.render_graph.scenes")))
        start = round(start + duration, 9)
    return RenderGraph(f"{intent.mode}_manifest_v1", width, height, fps,
                       tuple(scenes), _canonical(manifest, "$.render_graph"),
                       _canonical(report, "$.render_graph.report"))


__all__ = ["CreativeIntent", "MotionDecision", "MotionPlan", "RenderScene",
           "RenderGraph", "creative_intent", "plan_motion", "render_graph"]
