"""Pure, deterministic 2D coordinate transforms for future shared scene graphs.

This module intentionally has no renderer dependencies. Affines use column-vector
semantics: ``x' = a*x + c*y + e`` and ``y' = b*x + d*y + f``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar


class Space(str, Enum):
    LOCAL = "local"
    PARENT = "parent"
    WORLD = "world"
    CAMERA = "camera"
    VIEWPORT = "viewport"


class CoordinateSpace:
    """Static typing marker; runtime transform frames use :class:`Space`."""


class LocalSpace(CoordinateSpace):
    pass


class ParentSpace(CoordinateSpace):
    pass


class WorldSpace(CoordinateSpace):
    pass


class CameraSpace(CoordinateSpace):
    pass


class ViewportSpace(CoordinateSpace):
    pass


S = TypeVar("S", bound=CoordinateSpace)
T = TypeVar("T", bound=CoordinateSpace)


def _finite(*values: float, label: str = "values") -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{label} must be finite")


@dataclass(frozen=True)
class Point(Generic[S]):
    x: float
    y: float

    def __post_init__(self) -> None:
        _finite(self.x, self.y, label="Point coordinates")


@dataclass(frozen=True)
class Bounds(Generic[S]):
    """Axis-aligned bounds, represented by left/top/right/bottom edges."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        _finite(self.left, self.top, self.right, self.bottom,
                label="Bounds coordinates")
        if self.right < self.left or self.bottom < self.top:
            raise ValueError("Bounds edges must be ordered")

    @property
    def corners(self) -> tuple[Point[S], Point[S], Point[S], Point[S]]:
        return (Point(self.left, self.top), Point(self.right, self.top),
                Point(self.right, self.bottom), Point(self.left, self.bottom))


@dataclass(frozen=True)
class Affine2D(Generic[S, T]):
    """A typed 2D affine map from ``source`` coordinates to ``target``."""

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0
    source: Space = Space.LOCAL
    target: Space = Space.PARENT

    def __post_init__(self) -> None:
        _finite(self.a, self.b, self.c, self.d, self.e, self.f,
                label="Affine coefficients")
        if not isinstance(self.source, Space) or not isinstance(self.target, Space):
            raise ValueError("Affine source and target must be supported coordinate spaces")

    def apply(self, point: Point[S]) -> Point[T]:
        return Point(self.a * point.x + self.c * point.y + self.e,
                     self.b * point.x + self.d * point.y + self.f)

    def map_bounds(self, bounds: Bounds[S]) -> Bounds[T]:
        points = tuple(self.apply(point) for point in bounds.corners)
        return Bounds(min(point.x for point in points),
                      min(point.y for point in points),
                      max(point.x for point in points),
                      max(point.y for point in points))

    def then(self, following: Affine2D[T, object]) -> Affine2D[S, object]:
        """Compose this map followed by ``following`` (``following @ self``)."""
        if self.target is not following.source:
            raise ValueError(
                f"Cannot compose {self.target.value} -> {following.target.value}: "
                f"next map starts in {following.source.value}"
            )
        return Affine2D(
            a=following.a * self.a + following.c * self.b,
            b=following.b * self.a + following.d * self.b,
            c=following.a * self.c + following.c * self.d,
            d=following.b * self.c + following.d * self.d,
            e=following.a * self.e + following.c * self.f + following.e,
            f=following.b * self.e + following.d * self.f + following.f,
            source=self.source, target=following.target,
        )

    def inverse(self) -> Affine2D[T, S]:
        determinant = self.a * self.d - self.b * self.c
        if not math.isfinite(determinant) or determinant == 0.0:
            raise ValueError("Singular affine transform has no inverse")
        return Affine2D(
            a=self.d / determinant, b=-self.b / determinant,
            c=-self.c / determinant, d=self.a / determinant,
            e=(self.c * self.f - self.d * self.e) / determinant,
            f=(self.b * self.e - self.a * self.f) / determinant,
            source=self.target, target=self.source,
        )


@dataclass(frozen=True)
class TransformNode:
    """Hierarchy edge: node-local to parent-local, or root-local to world."""

    node_id: str
    transform: Affine2D
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("Node id cannot be empty")
        expected = Space.WORLD if self.parent_id is None else Space.PARENT
        if self.transform.source is not Space.LOCAL or self.transform.target is not expected:
            raise ValueError(f"Hierarchy edge must map local -> {expected.value}")


class TransformHierarchy:
    """Explicit tree/forest of local transforms with bounded traversal."""

    def __init__(self, *, max_depth: int = 128) -> None:
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 1:
            raise ValueError("max_depth must be a positive integer")
        self.max_depth = max_depth
        self._nodes: dict[str, TransformNode] = {}

    def add(self, node: TransformNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"Duplicate transform node {node.node_id!r}")
        if node.parent_id is not None and node.parent_id not in self._nodes:
            raise ValueError(f"Unknown parent node {node.parent_id!r}")
        self._nodes[node.node_id] = node
        try:
            self.world_transform(node.node_id)  # validates depth/cycles at insertion
        except ValueError:
            del self._nodes[node.node_id]
            raise

    def reparent(self, node_id: str, parent_id: str | None) -> None:
        if node_id not in self._nodes:
            raise ValueError(f"Unknown transform node {node_id!r}")
        if parent_id is not None and parent_id not in self._nodes:
            raise ValueError(f"Unknown parent node {parent_id!r}")
        old = self._nodes[node_id]
        target = Space.WORLD if parent_id is None else Space.PARENT
        replacement = TransformNode(
            node_id, Affine2D(old.transform.a, old.transform.b, old.transform.c,
                              old.transform.d, old.transform.e, old.transform.f,
                              Space.LOCAL, target), parent_id,
        )
        self._nodes[node_id] = replacement
        try:
            self.world_transform(node_id)
        except ValueError:
            self._nodes[node_id] = old
            raise

    def world_transform(self, node_id: str) -> Affine2D:
        try:
            node = self._nodes[node_id]
        except KeyError as exc:
            raise ValueError(f"Unknown transform node {node_id!r}") from exc
        chain: list[TransformNode] = []
        visited: set[str] = set()
        current = node
        while True:
            if current.node_id in visited:
                raise ValueError("Cyclic transform hierarchy")
            visited.add(current.node_id)
            chain.append(current)
            if len(chain) > self.max_depth:
                raise ValueError(f"Transform hierarchy exceeds depth limit {self.max_depth}")
            if current.parent_id is None:
                break
            try:
                current = self._nodes[current.parent_id]
            except KeyError as exc:
                raise ValueError(f"Unknown parent node {current.parent_id!r}") from exc

        # Each edge's PARENT frame is the next node's LOCAL frame. The frame
        # relabeling is explicit here; numeric affine composition is unchanged.
        result = chain[0].transform
        for parent in chain[1:]:
            edge = result
            relabeled = Affine2D(edge.a, edge.b, edge.c, edge.d, edge.e, edge.f,
                                 Space.LOCAL, Space.LOCAL)
            result = relabeled.then(parent.transform)
        return Affine2D(result.a, result.b, result.c, result.d, result.e, result.f,
                        Space.LOCAL, Space.WORLD)


@dataclass(frozen=True)
class Viewport:
    width: float
    height: float
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.width, self.height, self.scale_x, self.scale_y,
                self.offset_x, self.offset_y, label="Viewport values")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Viewport dimensions must be positive")
        if self.scale_x == 0 or self.scale_y == 0:
            raise ValueError("Viewport scale must be non-zero")

    @property
    def camera_to_viewport(self) -> Affine2D:
        return Affine2D(self.scale_x, 0, 0, self.scale_y,
                        self.offset_x, self.offset_y,
                        Space.CAMERA, Space.VIEWPORT)


def world_to_viewport(point: Point[WorldSpace],
                      world_to_camera: Affine2D[WorldSpace, CameraSpace],
                      viewport: Viewport) -> Point[ViewportSpace]:
    if world_to_camera.source is not Space.WORLD or world_to_camera.target is not Space.CAMERA:
        raise ValueError("Camera transform must map world -> camera")
    return world_to_camera.then(viewport.camera_to_viewport).apply(point)


def world_bounds_to_viewport(bounds: Bounds[WorldSpace],
                             world_to_camera: Affine2D[WorldSpace, CameraSpace],
                             viewport: Viewport) -> Bounds[ViewportSpace]:
    if world_to_camera.source is not Space.WORLD or world_to_camera.target is not Space.CAMERA:
        raise ValueError("Camera transform must map world -> camera")
    return world_to_camera.then(viewport.camera_to_viewport).map_bounds(bounds)
