"""Parametric motion-design components and scene compositions.

The public names are re-exported lazily so importing shared component types
does not load every scene builder and its renderer dependencies.
"""
from .base import BuiltScene, SceneContext

__all__ = ["BuiltScene", "SceneContext", "BUILDERS", "build_scene"]


def __getattr__(name: str):
    if name in {"BUILDERS", "build_scene"}:
        from . import scenes

        value = getattr(scenes, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
