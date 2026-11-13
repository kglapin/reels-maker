"""Shared scene build context and immutable render result models."""
from __future__ import annotations

import math
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
    _subtree_settles: dict = field(default_factory=dict, repr=False,
                                   compare=False)
    _settled_samples: dict = field(default_factory=dict, repr=False,
                                   compare=False)

    @property
    def duration(self) -> float:
        return self.context.duration

    @property
    def fps(self) -> int:
        return self.context.fps

    # Kinds whose sampled props depend on the frame time itself; their
    # subtrees can never reuse a settled sample.
    _TIME_DEPENDENT = frozenset({"video", "mesh3d", "sequence", "iso-world"})

    def _subtree_settle(self, node: Node) -> float:
        """Latest time at which any track in this subtree can still change.

        ``math.inf`` marks subtrees that sample differently every frame
        (video/sequence playback time), so they are never cached.
        """
        key = id(node)
        cached = self._subtree_settles.get(key)
        if cached is not None:
            return cached
        settle = 0.0
        for descendant in node.flatten():
            if descendant.kind in self._TIME_DEPENDENT:
                settle = math.inf
                break
            for track in descendant.tracks.values():
                end = track.end
                if end > settle:
                    settle = end
        self._subtree_settles[key] = settle
        return settle

    def at(self, time: float) -> list[Node]:
        sampled = []
        for node in self.nodes:
            # Once every track in a subtree has ended, sampling is constant;
            # reuse the first settled sample instead of copying the subtree
            # and re-evaluating every keyframe on each frame.
            if self._subtree_settle(node) <= time:
                entry = self._settled_samples.get(id(node))
                if entry is None:
                    entry = node.sample(time)
                    self._settled_samples[id(node)] = entry
                sampled.append(entry)
            else:
                sampled.append(node.sample(time))
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
