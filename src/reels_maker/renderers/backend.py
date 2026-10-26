"""Stable dispatch boundary for the classic and Studio renderers.

The renderer functions remain public and backward compatible. New orchestration
code should use :func:`render_with_backend`, which gives both engines the same
request shape while preserving their existing report dictionaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from ..ffmpeg import RenderError

RenderReport = dict[str, Any]


@dataclass(frozen=True)
class BackendOptions:
    """Options shared by renderer dispatch, with engine-specific fields."""

    output: str | Path | None = None
    root: str | Path | None = None
    cache_dir: str | Path | None = None
    cache: bool = True
    jobs: int | None = None
    profile: str | None = None
    supersample: int | None = None
    title_engine: str | None = None
    progress: Callable[[dict], None] | None = None


class RenderBackend(Protocol):
    """A renderer that accepts a project plus the common option envelope."""

    name: str

    def render(self, project: Any, options: BackendOptions) -> RenderReport:
        """Render one project and return its existing machine-readable report."""


class _LegacyBackend:
    name = "legacy"

    def render(self, project: Any, options: BackendOptions) -> RenderReport:
        if options.profile is not None or options.supersample is not None \
                or options.progress is not None:
            raise RenderError(
                "profile, supersample and progress options require the Studio backend")
        from ..renderer import render

        call_options = {
            "output": Path(options.output) if options.output is not None else None,
            "cache_dir": (Path(options.cache_dir)
                          if options.cache_dir is not None else None),
            "cache": options.cache,
            "jobs": options.jobs if options.jobs is not None else 2,
            "title_engine": options.title_engine or "legacy",
        }
        if options.root is not None:
            call_options["root"] = Path(options.root)
        return render(project, **call_options)


class _StudioBackend:
    name = "studio"

    def render(self, project: Any, options: BackendOptions) -> RenderReport:
        if options.jobs is not None or options.title_engine is not None:
            raise RenderError(
                "jobs and title_engine options belong to the classic backend")
        from .studio import render_studio

        return render_studio(
            project,
            output=options.output,
            profile=options.profile,
            supersample=options.supersample,
            cache_dir=options.cache_dir,
            cache=options.cache,
            progress=options.progress,
        )


_BACKENDS: dict[str, RenderBackend] = {
    "legacy": _LegacyBackend(),
    "studio": _StudioBackend(),
}


def get_backend(name: str) -> RenderBackend:
    """Return an available backend or raise a clear configuration error."""
    try:
        return _BACKENDS[name]
    except KeyError as exc:
        raise RenderError(
            f"Unknown render backend {name!r}; choose {', '.join(_BACKENDS)}") from exc


def render_with_backend(name: str, project: Any,
                        options: BackendOptions | None = None) -> RenderReport:
    """Dispatch through the stable backend boundary.

    Existing backend report keys are deliberately preserved so CLI/API callers
    can migrate incrementally without losing fields or changing schema v1.
    """
    return get_backend(name).render(project, options or BackendOptions())
