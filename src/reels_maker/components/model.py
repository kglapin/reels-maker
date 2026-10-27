"""Shared scene build context and immutable render result models."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.scene_graph import Node
from ..design.tokens import DesignTokens
from ..layout.engine import LayoutEngine, LayoutPlan
from ..motionkit.choreography import Choreography
from ..textkit.typesetter import FontBook


@dataclass
class SceneContext:
    width: int
    height: int
    fps: int
    duration: float
    tokens: DesignTokens
    style: str
    fonts: FontBook
    scene_index: int = 0
    seed: int = 0
    assets: object | None = None
    scene: dict = field(default_factory=dict)

    @property
    def layout(self) -> LayoutEngine:
        return LayoutEngine(self.width, self.height, self.tokens)

    @property
    def palette(self):
        return self.tokens.palette


@dataclass
class BuiltScene:
    index: int
    scene: dict
    context: SceneContext
    layout: LayoutPlan
    background: dict
    nodes: list[Node]
    elements: dict[str, Node]
    choreography: Choreography
    meta: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.context.duration

    @property
    def fps(self) -> int:
        return self.context.fps

    def at(self, time: float) -> list[Node]:
        sampled = [node.sample(time) for node in self.nodes]
        # Stable sort keeps authored order for nodes without an explicit z-index.
        return sorted(sampled,
                      key=lambda node: float(node.props.get("z_index", 0.0)))

    def element(self, role: str) -> Node:
        if role not in self.elements:
            raise KeyError(f"Scene {self.index + 1} has no element {role!r}")
        return self.elements[role]

    def to_dict(self) -> dict:
        return {
            "scene": self.index + 1,
            "type": self.scene.get("type", self.scene.get("composition", "custom")),
            "composition": self.layout.recipe,
            "duration": round(self.duration, 4),
            "background": self.background.get("kind", "solid"),
            "layout": self.layout.describe(),
            "choreography": self.choreography.to_dict(),
            **self.meta,
        }
