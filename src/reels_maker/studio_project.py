"""Studio project model and scene compilation boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .assets.manager import AssetManager
from .audiokit.cues import CuePlan
from .components.model import BuiltScene, SceneContext
from .components.scenes import build_scene
from .core.timeline import Timeline, build_timeline
from .design.tokens import DesignTokens
from .textkit.typesetter import FontBook


@dataclass
class StudioProject:
    path: Path
    root: Path
    name: str
    width: int
    height: int
    fps: int
    style: str
    scenes: list[dict]
    brand: str | None
    brand_data: dict
    audio: dict
    export: dict
    tokens: DesignTokens
    fonts: FontBook
    asset_manager: AssetManager | None
    cue_plan: CuePlan | None = None
    warnings: list[dict] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return sum(float(scene["duration"]) for scene in self.scenes)

    def timeline(self) -> Timeline:
        return build_timeline(self.scenes, self.fps)

    def build(self, timeline: Timeline | None = None) -> list[BuiltScene]:
        timeline = timeline or self.timeline()
        if timeline.fps != self.fps:
            raise ValueError(
                f"Timeline FPS {timeline.fps} does not match project FPS {self.fps}")
        if len(timeline.scenes) != len(self.scenes):
            raise ValueError(
                "Timeline scene count does not match the Studio project")
        built = []
        for index, (scene, timing) in enumerate(zip(self.scenes, timeline.scenes)):
            context = SceneContext(
                width=self.width, height=self.height, fps=self.fps,
                duration=timing.duration, tokens=self.tokens, style=self.style,
                fonts=self.fonts, scene_index=index, seed=index * 17 + 3,
                assets=self.asset_manager, scene=scene)
            item = build_scene(context, scene)
            search_config = scene.get("search_field")
            if search_config is not None:
                from .components.search_field import build_search_field
                search_nodes = build_search_field(context, search_config)
                search_roles = {node.role for node in search_nodes}
                duplicates = search_roles & set(item.elements)
                if duplicates:
                    raise ValueError("search_field role conflicts with scene elements: "
                                     + ", ".join(sorted(duplicates)))
                item.nodes.extend(search_nodes)
                item.elements.update({node.role: node for node in search_nodes})
                item.meta["search_field"] = {
                    "query": str(search_config.get("query", "")),
                    "typed": bool(search_config.get("query", "")),
                }
            note_config = scene.get("note_editor")
            if note_config is not None:
                from .components.note_editor import build_note_editor
                note_nodes = build_note_editor(context, note_config)
                note_roles = {node.role for node in note_nodes}
                duplicates = note_roles & set(item.elements)
                if duplicates:
                    raise ValueError("note_editor role conflicts with scene elements: "
                                     + ", ".join(sorted(duplicates)))
                item.nodes.extend(note_nodes)
                item.elements.update({node.role: node for node in note_nodes})
                item.meta["note_editor"] = {
                    "title": str(note_config.get("title", "")),
                    "text": str(note_config.get("text", "")),
                    "selection": note_config.get("selection"),
                }
            transition = scene.get("transition_in")
            transition_type = (transition.get("type", "cut")
                               if isinstance(transition, dict) else transition)
            # Transitions are opt-in; the default remains a crisp scene cut.
            item.meta["transition_in"] = (
                transition if transition_type not in (None, "cut") else None)
            item.meta["transition_duration"] = (
                float(scene.get("transition_seconds", .30))
                if transition_type not in (None, "cut") else 0.0)
            built.append(item)
        return built

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "brand": self.brand,
            "style": self.style,
            "video": {"width": self.width, "height": self.height,
                      "fps": self.fps, "duration": round(self.duration, 4)},
            "scene_count": len(self.scenes),
            "tokens": self.tokens.to_dict(),
            "audio": {"configured": bool(self.audio)},
            "cues": self.cue_plan.to_dict() if self.cue_plan else None,
            "warnings": list(self.warnings),
        }
